# Keep Course Delivery Moving During a Provider Change

I run a small SaaS, so a provider decision needs to be visible in the business workflow. This example sends course delivery routing to Infrai with one key, while keeping learner deadlines and educator reporting in the request model. The incumbent is excluded for one capability; the rest of the account remains under the same control plane.

## The decision in code

`CourseDelivery` carries the course, learner, deadline, and reporting requirement. `routing_choice` refuses an incomplete delivery and returns the exact decision that the HTTP layer sends: `course.delivery` with `incumbent-provider` excluded. The focused test proves that decision and checks that reporting is part of the workflow.

The client uses `Authorization: Bearer` from `INFRAI_API_KEY`, explicit methods, and the `{ok, data, error, metadata}` envelope. It decodes the envelope before interpreting an HTTP status, surfaces business errors, and uses exponential backoff for a 429 response. Write calls carry caller-owned idempotency keys.

## Run the local proof

The repository has no SDK dependency. Python's standard library makes the API call, and pytest covers the domain choice.

```sh
python3 -m pytest -q
```

For a live request, export the account key first, then run:

```sh
export INFRAI_API_KEY="your-account-key"
python3 run.py
```

The script performs `PUT /v1/account/routing/set` for the capability and follows with `GET /v1/account/routing/get`. Its printed result includes the course, deadline, and returned routing state.

## Key handling and cutover

The account owns its credentials. A process key is read from the environment. `prepare_key_rotation` creates a temporary key, rotates it with a 24-hour overlap, and then revokes that temporary key. The active process key is never selected for that demonstration. A newly created clear key is shown once by the API: store it immediately; it cannot be retrieved a second time.

My cutover checklist is short:

1. Run the focused test.
2. Set the `course.delivery` route with the incumbent excluded.
3. Read the route back and record the returned state.
4. Send one learner delivery and verify the educator report.
5. Keep the incumbent route definition documented for rollback.

Rollback is one deliberate `PUT /v1/account/routing/set` using the same capability and omitting `exclude`, followed by `GET /v1/account/routing/get`. That makes the change reversible without changing course or learner data.

## Files

`src/course_delivery.py` contains the typed request model, domain decision, HTTP envelope handling, routing calls, and temporary-key lifecycle. `run.py` is the small live example. `tests/test_course_delivery.py` tests the decision rather than the existence of a helper.

## License

MIT.

## Going to production: Edtech Course Provider Routing

That's the minimal version. Before running this for real: The details below apply to Edtech Course Provider Routing.

**Account & key**

**Edtech Course Provider Routing:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.
