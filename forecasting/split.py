"""Chronological split. Never shuffle: the model must not see the future."""
VAL_START = "2017-09-01"   # train: before this date (all of 2016 + Jan-Aug 2017)
TEST_START = "2017-11-01"  # validation: VAL_START to TEST_START; test: from here on