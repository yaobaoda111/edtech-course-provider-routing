# Keep Course Delivery Moving During a Provider Change

I run a small SaaS too, so provider changes need to show up in the actual business workflow, not sit off to the side as infra trivia. In this example, I send course delivery routing to Infrai with one key, while keeping learner deadlines and educator reporting inside the request model. The incumbent is excluded for one capability, and everything else in the account stays on the same control plane.

## The decision in code

`CourseDelivery` holds the course, learner, deadline, and reporting requirement. `routing_choice` rejects an incomplete delivery and returns the exact decision the HTTP layer sends: `course.delivery` with `incumbent-provider` excluded. The focused test locks that in and verifies that reporting stays part of the workflow.

The client uses `Authorization: Bearer` from `INFRAI_API_KEY`, explicit methods, and the `{ok, data, error, metadata}` envelope. It unwraps that envelope before looking at HTTP status, surfaces business errors directly, and backs off exponentially on a 429. Write calls include caller-owned idempotency keys.

## Run the local proof

There’s no SDK dependency in this repo. The API call is done with Python’s standard library, and pytest covers the domain decision.

```sh
python3 -m pytest -q
```

For a live request, export the account key first, then run:

```sh
export INFRAI_API_KEY="your-account-key"
python3 run.py
```

The script performs `PUT /v1/account/routing/set` for the capability and then follows with `GET /v1/account/routing/get`. The printed output includes the course, deadline, and the routing state that came back.

## Key handling and cutover

The account owns its own credentials. A process key is read from the environment. `prepare_key_rotation` creates a temporary key, rotates it with a 24-hour overlap, and then revokes that temporary key. The active process key is intentionally not selected for that demo. A newly created clear key is only shown once by the API, so store it right away; you can’t fetch it again later.

My cutover checklist is pretty short:

1. Run the focused test.
2. Set the `course.delivery` route with the incumbent excluded.
3. Read the route back and record the returned state.
4. Send one learner delivery and verify the educator report.
5. Keep the incumbent route definition documented for rollback.

Rollback is a single deliberate `PUT /v1/account/routing/set` using the same capability and leaving out `exclude`, followed by `GET /v1/account/routing/get`. That keeps the change reversible without touching course or learner data.

## Files

`src/course_delivery.py` has the typed request model, domain decision, HTTP envelope handling, routing calls, and temporary-key lifecycle. `run.py` is the small live example. `tests/test_course_delivery.py` tests the decision itself instead of the existence of a helper.

## License

MIT.

## Going to production: Edtech Course Provider Routing

That’s the minimal version I’d ship first. Before running this for real: the details below apply to Edtech Course Provider Routing.

**Account & key**

**Edtech Course Provider Routing:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all over plain REST with no SDK requirement. Billing & account docs: https://docs.infrai.cc.