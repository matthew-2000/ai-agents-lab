# 04 - Travel Planner Agent

## Status

Planned.

## Objective

Build a travel planning assistant that reasons under explicit constraints such as budget, time, and user preferences.

## v0 Scope

- Focus on planning only, not booking or real-world transactions.
- Accept a destination or trip idea plus a few concrete constraints from the user.
- Produce a structured itinerary or recommendation set with visible tradeoffs.
- Make assumptions explicit when the input is incomplete.
- Use simple tools or mock data for costs, timing, or weather when useful.
- Keep the domain narrow enough that answers can still be evaluated case by case.

## Done Criteria

- The agent returns plans that respect the stated budget, timing, and preference constraints.
- Assumptions are surfaced clearly instead of being hidden in the output.
- Tradeoffs are explained when constraints compete with each other.
- Edge cases such as missing budget or conflicting preferences are covered by evals.
