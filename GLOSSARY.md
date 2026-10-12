# Glossary

Every term in plain language.

**Decision model.** A model that answers a question by choosing among options you give it, rather than by writing text. It returns a number for each option. Jev and Laya are decision models. A chat model like GPT or Claude is not.

**State.** What the model is asked about. Here, the complaint the person typed.

**Typed question.** A question whose kind of answer is fixed in advance. This demo uses one kind, a Choice. Decision models also offer Score (a place on a scale) and Noul (the chance a yes-or-no statement is true).

**Choice.** A typed question with a fixed list of options, each with an optional description. The model must pick one of them; it cannot invent another.

**Criteria.** The options in a Choice, with their descriptions. Here, the four teams and their scopes.

**Scope.** A team's description: what it owns, in plain words. It guides the model and is shown to the person as the reason for a routing.

**Distribution.** The model's number for every option, adding up to 1. The bar chart on screen. It shows not just the pick but what the model weighed it against.

**Confidence.** One number from 0 to 1 for how settled the distribution is. High when one option dominates; low when several are close. Laya computes it from the distribution's entropy.

**Calibration.** Whether a confidence of 0.7 really means right about 70% of the time. Laya's shipped calibration is off, so its confidence ranks routings (higher is more trustworthy) but is not a probability.

**Threshold.** The confidence below which code stops trusting the model. Here, `UNSURE_BELOW = 0.3`. Below it, the demo flags the routing; a production system would send it to a person.

**Backend.** The piece of code that calls the model. Swap the backend and the rest of the application is unchanged.

**Revision.** A specific saved version of the model's files, named by a commit hash. Pinning it means every user downloads exactly the version this demo was tested with.

**Grade.** The share of routings the person agreed with, as a letter: A from 90%, B from 80%, C from 70%, D from 60%, otherwise F.
