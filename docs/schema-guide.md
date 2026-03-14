# Schema Guide

Schemas are YAML files in the `schemas/` directory. Each one defines the shape, types, and constraints of the data you want to generate - the engine reads them on startup and exposes each as its own endpoint.

This is the full reference for every generator type. If you're starting from existing JSON data, skip to the [JSON to YAML converter](#json-to-yaml-converter) section at the bottom.

## Basic structure

Every schema is an object at the root:

```yaml
type: object
fields:
  field_name:
    type: <generator_type>
    # type-specific params
```

That's it. Fields can be nested objects, arrays of objects, optional values, union types - all composable.

---

## Generator types

### string

Three modes: template, Faker provider, or regex.

#### Template

```yaml
user_id:
  type: string
  template: "user-{nnnn}"
  n_type: numeric   # numeric | alphabetic | hex
```

`{n}` = one char, `{nn}` = two, `{nnn}` = three, and so on.

```yaml
order_id:
  type: string
  template: "ORD-{nnnnnn}"
  n_type: numeric
  # → ORD-482761

session_id:
  type: string
  template: "sess_{nnnn}_{nnn}"
  n_type: hex
  # → sess_a4f2_b3c
```

#### Faker provider

Uses the [Faker](https://faker.readthedocs.io) library. Pass the provider as `string_type`:

```yaml
email:
  type: string
  string_type: "internet.email"

full_name:
  type: string
  string_type: "person.name"

city:
  type: string
  string_type: "address.city"
```

Common providers: `internet.email`, `internet.url`, `person.name`, `person.first_name`, `person.last_name`, `address.city`, `address.country`, `address.street_address`, `company.name`, `lorem.word`, `lorem.sentence`, `misc.uuid4`.

#### Regex

```yaml
phone:
  type: string
  regex: "\\+1-[0-9]{3}-[0-9]{3}-[0-9]{4}"
```

#### Plain string with length bounds

```yaml
description:
  type: string
  min_length: 10
  max_length: 100
```

---

### int

```yaml
age:
  type: int
  min: 18
  max: 90

score:
  type: int
  min: 0
  max: 100
  step: 5   # optional - values will be multiples of step
```

---

### float

```yaml
price:
  type: float
  min: 0.99
  max: 999.99
  precision: 2   # decimal places
```

---

### bool

```yaml
is_active:
  type: bool
  p_true: 0.8   # 80% chance of true (default 0.5)
```

---

### enum

Pick from a fixed list. Weights are optional - omit for uniform distribution.

```yaml
status:
  type: enum
  values: [pending, active, cancelled, completed]

tier:
  type: enum
  values: [free, pro, enterprise]
  weights: [60, 30, 10]   # 60% free, 30% pro, 10% enterprise
```

---

### datetime

Generates formatted datetime strings within a range.

```yaml
created_at:
  type: datetime
  start: "2024-01-01T00:00:00Z"
  end: "2024-12-31T23:59:59Z"
  format: "%Y-%m-%dT%H:%M:%SZ"
```

---

### timestamp

Unix timestamps in microseconds.

```yaml
event_ts:
  type: timestamp
  start: '2025-01-01T00:00:00+00:00'
  end:   '2026-01-01T00:00:00+00:00'
```

---

### stateful_datetime

Auto-incrementing datetime - each generated record advances the value by `increment` seconds. Useful for streaming scenarios where you want realistic time progression.

```yaml
event_time:
  type: stateful_datetime
  start: "2024-01-01T00:00:00Z"
  increment: 1        # seconds per record
  format: "%Y-%m-%dT%H:%M:%SZ"
```

---

### stateful_timestamp

Same idea, but as a Unix microsecond timestamp.

```yaml
event_ts:
  type: stateful_timestamp
  start: '2025-01-01T00:00:00+00:00'
  increment: 1000000   # microseconds per record (= 1 second)
```

---

### array

Generate a list of items. Child can be any generator type.

```yaml
tags:
  type: array
  min_items: 1
  max_items: 5
  child:
    type: string
    string_type: "lorem.word"

line_items:
  type: array
  min_items: 1
  max_items: 10
  child:
    type: object
    fields:
      sku:
        type: string
        template: "SKU-{nnnn}"
      qty:
        type: int
        min: 1
        max: 20
      price:
        type: float
        min: 1.00
        max: 500.00
        precision: 2
```

---

### object

Nested object with typed fields. Can be nested arbitrarily deep.

```yaml
address:
  type: object
  fields:
    street:
      type: string
      string_type: "address.street_address"
    city:
      type: string
      string_type: "address.city"
    zip:
      type: string
      regex: "[0-9]{5}"
```

---

### maybe

Wraps any generator and makes it nullable. `p_null` controls how often it returns null.

```yaml
middle_name:
  type: maybe
  p_null: 0.6   # 60% chance of null
  child:
    type: string
    string_type: "person.first_name"
```

---

### one_of

Union type - pick one of several generator specs. Weights are optional.

```yaml
payload:
  type: one_of
  choices:
    - type: object
      fields:
        click_target:
          type: string
          string_type: "internet.url"
    - type: object
      fields:
        search_query:
          type: string
          string_type: "lorem.sentence"
    - type: int
      min: 0
      max: 999
  weights: [50, 30, 20]
```

---

### select

Generates a partial object - picks N fields from a list of options. Good for schemas where not every record has the same set of fields.

```yaml
properties:
  type: select
  pick: 2   # how many fields to include per record
  options:
    - page_url:
        type: string
        string_type: "internet.url"
    - referrer:
        type: string
        string_type: "internet.url"
    - duration_ms:
        type: int
        min: 100
        max: 30000
    - scroll_depth:
        type: float
        min: 0.0
        max: 1.0
        precision: 2
```

---

## Entity correlation

By default every field is generated independently. That means if `user_id = "user_042"` shows up in record 1 and record 7, `full_name` will be different both times. For pipeline testing thats often a problem - you want the same user to always have the same name, email, tier, etc.

`bound_to` (or its alias `linked_to`, same thing) fixes this.

```yaml
type: object
fields:
  user_id:
    type: string
    template: "user_{nnn}"
    n_type: numeric

  full_name:
    type: string
    string_type: "person.name"
    bound_to: user_id   # same user_id → always same full_name

  age:
    type: int
    min: 18
    max: 75
    bound_to: user_id

  tier:
    type: enum
    values: [free, pro, enterprise]
    weights: [60, 30, 10]
    bound_to: user_id

  # not correlated - random every record
  event_type:
    type: enum
    values: [login, purchase, logout, view]
```

Generate 20 records and you'll see `user_042` always has the same name, age, and tier - even across separate requests.

**Rules:**
- The anchor field (`user_id` above) must be declared **before** the fields that reference it.
- Uses Redis under the hood. Requires the Redis service to be running.
- Correlated values survive across requests - the cache doesn't expire until you flush Redis.
- Chaos operations run after correlation lookup, so they can still mutate the output but won't affect what's stored in the cache.
- `stateful_datetime` and `stateful_timestamp` fields cannot be correlated - you'll get an error at schema load time if you try.

### Cross-schema correlation

Sometimes you want two different schemas to share the same entity cache. For example, an `order` schema where `user_id` should resolve to the same `full_name` and `tier` that the `user_profile` schema already populated.

```yaml
# in your order schema
user_id:
  type: string
  template: "user_{nnn}"
  n_type: numeric

full_name:
  type: string
  string_type: "person.name"
  bound_to: user_id
  bound_to_schema: user_profile   # look up cache from this schema

tier:
  type: enum
  values: [free, pro, enterprise]
  bound_to: user_id
  bound_to_schema: user_profile
  bound_to_revision: 5            # optional - pin to a specific revision, omit for latest
```

Cache misses fall back to independent generation with a warning in the logs. The order schema never writes into the user_profile namespace - it only reads.

---

## JSON to YAML converter

If you already have JSON samples of your data, you can bootstrap a schema from them instead of writing one from scratch.

```bash
# from a file
python tools/json_to_schema.py example.json -o schemas/user.yaml

# pipe from anywhere
curl https://api.example.com/events | python tools/json_to_schema.py > schemas/events.yaml

# multiple samples - infers realistic min/max ranges
python tools/json_to_schema.py samples.json --infer-arrays --sample-size 100
```

The tool auto-detects types, recognizes email/URL patterns, infers numeric ranges from samples, and wraps null fields in `maybe`. Output is a ready-to-use YAML schema - you'll probably still want to tune it, but it saves the tedious part.
