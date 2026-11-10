# Research context and contribution

This project studies a narrow question about exact tool permissions and approval burden. It does not introduce prompt injection research or claim that external enforcement is a new idea.

[AgentDojo](https://arxiv.org/abs/2406.13352) evaluates agents operating over untrusted tool data using realistic tasks, attacks, and defenses. It provides a stronger environment for a later external evaluation than this project's small synthetic pilot. The present benchmark independently authors its fixtures and does not copy AgentDojo tasks or claim comparable performance.

[Defeating Prompt Injections by Design](https://arxiv.org/abs/2503.18813) introduces CaMeL, which separates control and data flows and uses capability-based policies to constrain tool calls. This project's simple argument matcher is not an implementation of CaMeL and provides no information-flow guarantees.

The intended contribution is a transparent comparison of attempted violations, executed violations, authorized completion, and approval burden under matched conditions. Its value depends on realistic independent tasks and informative failure analysis, rather than demonstrating the expected fact that a correct gate blocks the actions it was designed to block.
