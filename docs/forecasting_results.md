# Day-ahead forecasting results

Test window: 1 Nov to 31 Dec 2016 (1,464 hours per building). Train: before 1 Sep 2016. Validation (early stopping only): Sep to Oct.
Metric: WAPE (0.10 = 10% of total load). One LightGBM model per building vs the best of "same hour yesterday" and "same hour last week".

| Building | LightGBM WAPE | Best baseline WAPE |
|---|---|---|
| B01 Academic Block | 0.120 | 0.131 |
| B02 Library | 0.130 | 0.143 |
| B03 Hostel | 0.042 | 0.048 |
| B04 Admin Block | 0.179 | 0.226 |
| B05 Engineering Labs | 0.119 | 0.134 |

Caveats:
- Meter load is real BDG2 data (Fox site, US). The calendar is an approximate US academic calendar. These patterns are borrowed, not Coimbatore data.
- Weather inputs are observed values, so the scores assume a perfect weather forecast.
- One chronological split with a 61-day test window that includes holidays. Results are indicative, not final.
- The top features for every building are past-load lags; calendar and weather add little so far.

## Experiment 2: two years of history (test: 1 Nov to 31 Dec 2017)

Train: Jan 2016 to Aug 2017. Validation (early stopping only): Sep to Oct 2017. Test: Nov to Dec 2017 (1,464 hours per building).
The calendar now also marks the Friday after Thanksgiving and 24-31 Dec as approximate university closure days (chosen from the usual academic calendar, not from load).

| Building | LightGBM WAPE | Best baseline WAPE |
|---|---|---|
| B01 Academic Block | 0.083 | 0.130 |
| B02 Library | 0.162 | 0.200 |
| B03 Hostel | 0.035 | 0.046 |
| B04 Admin Block | 0.128 | 0.173 |
| B05 Engineering Labs | 0.080 | 0.093 |

Caveats: the extra training year, the closure days and the test year all changed together, so the improvement over experiment 1 cannot be attributed to one cause. Weather is still observed, not forecast. Data is borrowed BDG2 (Fox site, US), not Coimbatore data.