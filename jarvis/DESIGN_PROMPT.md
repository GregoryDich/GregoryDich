# 🎨 DESIGN_PROMPT — промпт для генерации дизайна JARVIS (опционально)

Статус: **опция**. Текущий дизайн терминала остаётся рабочим; этот промпт — если
захочется получить внешний визуальный концепт (GPT-4o, Claude с артефактами,
v0.dev, Lovable; Midjourney — только для мудборда).

Как пользоваться:
1. Скопируй промпт из блока ниже целиком.
2. В последней строке подставь экран: `Screen focus: FIRE` (генерировать по одному
   экрану — качество выше).
3. Итерируй короткими правками (примеры в конце файла).
4. Результат (PNG или HTML/CSS) верни Клоду — токены будут перенесены в
   `frontend/src/theme.css`, компоненты переверстаны.

---

```text
You are a senior product designer who has shipped professional financial
terminals (Bloomberg Terminal, LSEG Workspace) and modern fintech products
(Linear, Mercury, Copilot Money). Design the UI for JARVIS — a personal
economic manager: a self-hosted, Bloomberg-class terminal for ONE person
whose mission is to guide the user to financial independence.

## Product essence
- The hero metric of the whole product is the "Freedom point": passive
  income (4% rule) vs monthly basic expenses. Everything else serves it.
- One user (IT student, Israel), dual currency USD/ILS, channels: US ETFs
  via IBKR, Tel-Aviv stock exchange, crypto, deposits.
- Data honesty is a core value: every number carries a source badge —
  live / delayed / demo — and demo data must be visibly, unmistakably demo.
- Advisory only: forecasts with reasoning, decisions belong to the human.
  Recommendation cards must feel like a calm analyst, not a casino.

## Information architecture
Docked multi-panel workspace (like Bloomberg Launchpad): panels live in a
docking shell (tabs, split views, pop-outs). Command palette (Ctrl+K) with
Bloomberg-style mnemonics is the primary navigation: FIRE, NAV, WEI, GP,
FA, EQS, ECO, NEWS, PORT, CAL, AI, ALRT.

Screens to design (in priority order):
1. FIRE — Freedom: progress to break-even point (hero visual), target
   capital, passive income vs expenses gap, scenario matrix
   (contribution × return → years), expense breakdown.
2. WEI — Markets overview: grouped quote monitors (indices, FX incl.
   USD/ILS, crypto, commodities), sector treemap heatmap, candlestick
   chart panel, watchlist table with sparklines.
3. PORT — Portfolio & Risk: positions blotter (USD + ILS values), stat
   tiles (value, P&L, VaR 95%, volatility, Sharpe, max drawdown),
   allocation donut, equity curve, trade entry + CSV import.
4. NAV — Allocation Navigator (the signature screen): channel cards
   (US ETFs / TASE / crypto / deposits), each with a recommended tranche
   (~$1000), probability bar of rise/flat/fall on the chosen horizon,
   cost breakdown (commissions, spreads, 25% capital-gains tax), and a
   one-line reasoning. Prominent but elegant disclaimer.
5. ECO — Macro: series explorer (US + Israel tabs), line charts, yield
   curve / 10Y–2Y recession spread, central-bank rate steps.
6. AI — Copilot: chat over your own data, generated charts inline,
   morning digest preview, alert configuration.
Plus: first-run onboarding wizard (8 questions, warm and personal, ends
with "Build my terminal"), and the Ctrl+K command palette.

## Visual direction
- Dark, dense, professional; "Bloomberg meets Linear". Data-ink first:
  chrome recedes, numbers and charts glow.
- Base palette to refine (current implementation): background #07090D,
  panel #0D1117, elevated #131926, border #1E2635, text #D7DCE6, muted
  #7D8698, accent amber #F5A623 (the "JARVIS energy" color), up #2FBF71,
  down #E5484D, info cyan #3FB1CE. You may propose a superior palette —
  keep amber as the brand accent and keep up/down colorblind-safe.
- Typography: humanist sans for labels (Inter/SF), tabular monospace for
  every numeral (JetBrains Mono / SF Mono); 12–13px base, tight leading;
  clear 4-level hierarchy from hero numbers (28–32px) to table cells.
- Components to specify: stat tile, data table (hover, sorted, sticky
  header), source badge (live pulse-dot / delayed / amber DEMO), progress
  meter for Freedom, probability bar (rise/flat/fall), channel card,
  chart frame with title row, command palette, onboarding step card,
  toast/alert. Consistent 4/8px spacing grid, 6px radius, subtle borders
  instead of shadows.
- Motion: restrained — 150–250ms ease-out on panel focus, number
  tick-up on load, pulse on live badge. No decorative animation.
- Charts: candlesticks green/red on transparent bg; macro lines single
  accent color with soft area fill; treemap saturation encodes magnitude.
- Language of UI copy: Russian (labels like «Свобода», «Цель», «Пассивный
  доход»), numerals Western. RTL not required.

## Deliverables
High-fidelity desktop mockups at 1600×950 for the 6 screens + onboarding
+ palette, plus a one-page component sheet with exact tokens (hex, px,
font sizes) that a React developer can transcribe into CSS variables.
Design must be implementable with plain CSS (no heavy UI kit): the shell
is Dockview, charts are TradingView lightweight-charts and ECharts.

Screen focus for this iteration: [SCREEN NAME] — render this one screen
at full fidelity first.
```

---

## Примеры итераций

- `Make the Freedom progress a radial gauge with the gap amount in the center.`
- `Try a colder slate palette; keep the amber accent.`
- `Denser: 11px tables, 24px row height, more panels per screen.`
- `Show the NAV channel card in three states: recommended / hold / avoid.`
- `Output the component sheet only, as HTML+CSS with exact CSS variables.`
