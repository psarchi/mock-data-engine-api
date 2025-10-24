from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from server.models import GenerateRequest, GenerateResponse, ValidateRequest
from server.deps import get_validator, get_settings
from faker_engine.api import build_generator, generate_many

router = APIRouter(prefix="/v1", tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, validator=Depends(get_validator),
             settings=Depends(get_settings)):
    # chaos/failure injection
    if settings.features.chaos.enabled:
        import random, time
        lo, hi = settings.features.chaos.latency_ms_range
        if hi and hi > 0:
            delay_ms = random.randint(int(lo), int(hi))
            time.sleep(delay_ms / 1000.0)
        for status_code_str, probability in settings.features.chaos.error_rates.items():
            try:
                status_code_int = int(status_code_str)
            except Exception:
                continue
            if random.random() < float(probability):
                raise HTTPException(status_code=status_code_int,
                                    detail="chaos")

    report = validator.validate(req.spec, raise_on_fail=False)
    if not report.ok:
        raise HTTPException(status_code=422, detail={
            "ok": False,
            "issues": [{
                "code": i.code,
                "path": list(i.path) if getattr(i, "path", None) else None,
                "msg": i.msg,
                "detail": getattr(i, "detail", None),
            } for i in report.issues]
        })
    gen = build_generator(report.normalized or req.spec)
    items = generate_many(gen, n=req.n, seed=req.seed, locale=req.locale)
    return {"items": items, "count": len(items)}
