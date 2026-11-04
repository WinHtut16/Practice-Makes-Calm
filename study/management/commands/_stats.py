"""Small statistics helpers without numpy."""


def icc_2_1(ratings):
    """ICC(2,1): two-way random effects, absolute agreement, single rater.

    ratings: list of rows, each row = scores from k raters for one item.
    """
    n, k = len(ratings), len(ratings[0])
    if n < 2:
        return float("nan")
    grand = sum(map(sum, ratings)) / (n * k)
    row_means = [sum(r) / k for r in ratings]
    col_means = [sum(r[j] for r in ratings) / n for j in range(k)]
    ss_rows = k * sum((m - grand) ** 2 for m in row_means)
    ss_cols = n * sum((m - grand) ** 2 for m in col_means)
    ss_total = sum((x - grand) ** 2 for r in ratings for x in r)
    ss_err = ss_total - ss_rows - ss_cols
    msr, msc = ss_rows / (n - 1), ss_cols / (k - 1)
    mse = ss_err / ((n - 1) * (k - 1))
    denom = msr + (k - 1) * mse + k * (msc - mse) / n
    return (msr - mse) / denom if denom else float("nan")


def cohen_kappa(a, b):
    """Cohen's kappa for two lists of binary (0/1) labels."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0
