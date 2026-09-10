-- File I/O totals for one user, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Users detail)
-- {user} is bound as a parameter, not inlined.
SELECT
    ios,
    io_latency
FROM
    sys.user_summary_by_file_io
WHERE
    user = %s
