-- I/O by file (bytes read/written), from the sys schema.
-- Called from: services/performance.py -> fetch_view() (Performance > I/O)
-- sys.io_global_by_file_by_bytes ranks files by total bytes of I/O, sorted by
-- descending total by default, so the hottest files are on top.
SELECT
    file,
    count_read,
    total_read,
    avg_read,
    count_write,
    total_written,
    avg_write,
    total,
    write_pct
FROM
    sys.io_global_by_file_by_bytes
