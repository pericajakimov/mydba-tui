-- File I/O totals for one host, from the sys schema.
-- Called from: services/performance.py -> fetch_breakdown() (Hosts detail)
-- {host} is bound as a parameter, not inlined.
SELECT
    ios,
    io_latency
FROM
    sys.host_summary_by_file_io
WHERE
    host = %s
