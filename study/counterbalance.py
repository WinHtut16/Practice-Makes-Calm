"""Counterbalancing: 6 design orders x 3 scenario rotations = 18 sequences (paper, Table 3)."""
import random

ORDERS = [
    ("C", "F", "A"),
    ("F", "A", "C"),
    ("A", "C", "F"),
    ("C", "A", "F"),
    ("A", "F", "C"),
    ("F", "C", "A"),
]
ROTATIONS = [
    ("S1", "S2", "S3"),  # R1
    ("S2", "S3", "S1"),  # R2
    ("S3", "S1", "S2"),  # R3
]


def sequence(n):
    """n in 1..18 -> list of (design, scenario) for blocks 1-3. P01 = order 1 x R1, P02 = order 1 x R2, ..."""
    if not 1 <= n <= 18:
        raise ValueError("sequence number must be 1-18")
    order = ORDERS[(n - 1) // 3]
    rot = ROTATIONS[(n - 1) % 3]
    return list(zip(order, rot))


def shuffled_assignment(seed):
    """Random order in which arriving participants receive sequence numbers."""
    nums = list(range(1, 19))
    random.Random(seed).shuffle(nums)
    return nums
