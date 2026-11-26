"""C05 reuses the immutable audited C04 row cache and native controls."""
from analysis.c05_models import WORK,CONTRACT
from analysis.c04_data import verify as verify_source

def verify():
    return verify_source()
