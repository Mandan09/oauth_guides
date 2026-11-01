# {{ g.app }}: OAuth app setup & approval guide

**Difficulty:** {{ g.difficulty }} · **Hands-on:** {{ g.hands_on_time }} · **Approval wait:** {{ g.approval_wait }} · **Production:** {{ g.time_to_production }}

{{ g.headline }}

{{ g.summary }}

## The path
{% for s in g.stages %}
### {{ loop.index }}. {{ s.name }} ({{ s.duration }}){% if s.blocking %} — blocking{% endif %}
{% for st in s.steps %}
- **[{{ st.owner }}] {{ st.title }}**{% if st.duration %} ({{ st.duration }}){% endif %}: {{ st.detail }}{% for i in st.source_ids %} [{{ i }}]{% endfor %}
{%- endfor %}
{% endfor %}
## What an agent can do
{% for x in g.agent_can %}- {{ x }}
{% endfor %}
## Where you take over
{% for x in g.you_must %}- {{ x }}
{% endfor %}
{% if g.permissions %}## Permissions your agent needs
| Action | Scopes | Review impact |
|---|---|---|
{% for p in g.permissions %}| {{ p.action }} | {{ p.scopes|join(', ') }} ({{ p.status }}) | {{ p.review_impact }} |
{% endfor %}
{% endif %}## Requirements
{% for c in g.requirements %}- ({{ c.status }}) {{ c.text }}{% for i in c.source_ids %} [{{ i }}]{% endfor %}
{% endfor %}
## Gotchas
{% for c in g.gotchas %}- ({{ c.status }}) {{ c.text }}{% for i in c.source_ids %} [{{ i }}]{% endfor %}
{% endfor %}
## If you get stuck
{% for b in g.blockers %}- **{{ b.issue }}** — {{ b.how_to_proceed }}
{% endfor %}
## Evidence
{% for c in g.key_claims %}- ({{ c.status }}) {{ c.text }}{% for i in c.source_ids %} [{{ i }}]{% endfor %}
{% endfor %}{% if g.probes %}
**Live probes**
{% for p in g.probes %}- `{{ p.request }}` → {{ p.result }}
{% endfor %}{% endif %}{% if g.assumptions %}
**Assumptions and estimates**
{% for a in g.assumptions %}- {{ a }}
{% endfor %}{% endif %}{% if g.open_questions %}
**Open questions**
{% for q in g.open_questions %}- {{ q }}
{% endfor %}{% endif %}
## Sources
{% for s in g.sources %}- [{{ s.id }}] [{{ s.title }}]({{ s.url }})
{% endfor %}
---
Generated {{ g.generated_at[:10] }} · {{ url }}
