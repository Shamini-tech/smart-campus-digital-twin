"""Build data/academic_calendar.csv for the Fox source site (2016-2017).

IMPORTANT: term, spring-break and finals dates are APPROXIMATE assumptions for a
typical US university in Arizona, not an official calendar. US federal
holidays are exact. The calendar is validated against observed load but never
built from it, so it cannot leak the forecasting target.
"""
from pathlib import Path

import pandas as pd

HOLIDAYS = {
    "2016-01-01": "New Year Day", "2016-01-18": "MLK Day", "2016-02-15": "Presidents Day",
    "2016-05-30": "Memorial Day", "2016-07-04": "Independence Day", "2016-09-05": "Labor Day",
    "2016-10-10": "Columbus Day", "2016-11-11": "Veterans Day", "2016-11-24": "Thanksgiving",
    "2016-12-26": "Christmas (observed)",
    "2017-01-02": "New Year Day (observed)", "2017-01-16": "MLK Day", "2017-02-20": "Presidents Day",
    "2017-05-29": "Memorial Day", "2017-07-04": "Independence Day", "2017-09-04": "Labor Day",
    "2017-10-09": "Columbus Day", "2017-11-10": "Veterans Day (observed)", "2017-11-23": "Thanksgiving",
    "2017-12-25": "Christmas",
}

# APPROXIMATE university closure days, from the usual academic calendar (NOT derived
# from load): the Friday after Thanksgiving and the winter closure, 24-31 Dec.
CLOSURE_DAYS = (
    ["2016-11-25", "2017-11-24"]
    + [f"2016-12-{d}" for d in range(24, 32)]
    + [f"2017-12-{d}" for d in range(24, 32)]
)
for _day in CLOSURE_DAYS:
    HOLIDAYS.setdefault(_day, "University closure (approx.)")

# (start, end, term); later entries override earlier ones
TERMS = [
    ("2016-01-01", "2016-01-10", "winter_break"),
    ("2016-01-11", "2016-05-06", "spring"),
    ("2016-05-07", "2016-08-21", "summer"),
    ("2016-08-22", "2016-12-09", "fall"),
    ("2016-12-10", "2017-01-08", "winter_break"),
    ("2017-01-09", "2017-05-05", "spring"),
    ("2017-05-06", "2017-08-20", "summer"),
    ("2017-08-21", "2017-12-08", "fall"),
    ("2017-12-09", "2017-12-31", "winter_break"),
]
SPRING_BREAKS = [("2016-03-07", "2016-03-11"), ("2017-03-06", "2017-03-10")]
FINALS_WEEKS = [
    ("2016-05-02", "2016-05-06"), ("2016-12-05", "2016-12-09"),
    ("2017-05-01", "2017-05-05"), ("2017-12-04", "2017-12-08"),
]

def build_calendar() -> pd.DataFrame:
    df = pd.DataFrame({"date": pd.date_range("2016-01-01", "2017-12-31", freq="D")})
    df["term"] = "none"
    for start, end, name in TERMS:
        df.loc[df["date"].between(start, end), "term"] = name
    for start, end in SPRING_BREAKS:
        df.loc[df["date"].between(start, end), "term"] = "spring_break"
    df["is_finals_week"] = False
    for start, end in FINALS_WEEKS:
        df.loc[df["date"].between(start, end), "is_finals_week"] = True
    df["weekday"] = df["date"].dt.day_name()
    df["is_weekend"] = df["date"].dt.day_of_week >= 5
    df["holiday_name"] = df["date"].dt.strftime("%Y-%m-%d").map(HOLIDAYS).fillna("")
    df["is_holiday"] = df["holiday_name"] != ""
    in_term = df["term"].isin(["spring", "fall"])
    df["is_class_day"] = in_term & ~df["is_weekend"] & ~df["is_holiday"] & ~df["is_finals_week"]
    return df


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "data" / "academic_calendar.csv"
    cal = build_calendar()
    cal.to_csv(out, index=False)
    print(f"Wrote {out}")
    print(cal["term"].value_counts().to_string())
    print("class days:", int(cal["is_class_day"].sum()), "holidays:", int(cal["is_holiday"].sum()))