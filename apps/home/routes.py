# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import json

from apps.home import blueprint
from flask import render_template, request
from flask_login import login_required
from jinja2 import TemplateNotFound
import pymysql



def get_daily_bandwidth():
    db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'syslog'
    }
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = """
    WITH RECURSIVE DateRange AS (
    SELECT '2024-06-11' AS date  -- Start date
    UNION ALL
    SELECT DATE_ADD(date, INTERVAL 1 DAY)
    FROM DateRange
    WHERE date < '2024-06-18'  -- End date
)
SELECT
    d.date,
    COALESCE(SUM(l.sentbyte) / 1048576, 0) AS total_sent_bytes
FROM DateRange d
LEFT JOIN logs l ON d.date = l.date
GROUP BY d.date
ORDER BY d.date;
"""
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    labels = [result['date'] for result in results]
    data_points = [result['total_sent_bytes'] for result in results]
    return labels, data_points


@blueprint.route('/index')
@login_required
def index():
    db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'syslog'
    }
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = """
    SELECT
    totalCountToday,
    totalCountYesterday,
    totalOutgoingToday,
    totalOutgoingYesterday,
    totalIncomingToday,
    totalIncomingYesterday,
    loginAttemptsToday,
    loginAttemptsYesterday,
    -- Comparisons: Is Today's count greater than Yesterday's?
    (totalCountToday > totalCountYesterday) AS isTotalCountGreater,
    (totalOutgoingToday > totalOutgoingYesterday) AS isTotalOutgoingGreater,
    (totalIncomingToday > totalIncomingYesterday) AS isTotalIncomingGreater,
    (loginAttemptsToday > loginAttemptsYesterday) AS isLoginAttemptsGreater,
    -- Percentage Changes
    IF(totalCountYesterday = 0 AND totalCountToday > 0, 100, IF(totalCountYesterday = 0, NULL, ((totalCountToday - totalCountYesterday) / totalCountYesterday * 100))) AS pctChangeTotalCount,
    IF(totalOutgoingYesterday = 0 AND totalOutgoingToday > 0, 100, IF(totalOutgoingYesterday = 0, NULL, ((totalOutgoingToday - totalOutgoingYesterday) / totalOutgoingYesterday * 100))) AS pctChangeTotalOutgoing,
    IF(totalIncomingYesterday = 0 AND totalIncomingToday > 0, 100, IF(totalIncomingYesterday = 0, NULL, ((totalIncomingToday - totalIncomingYesterday) / totalIncomingYesterday * 100))) AS pctChangeTotalIncoming,
    IF(loginAttemptsYesterday = 0 AND loginAttemptsToday > 0, 100, IF(loginAttemptsYesterday = 0, NULL, ((loginAttemptsToday - loginAttemptsYesterday) / loginAttemptsYesterday * 100))) AS pctChangeLoginAttempts
FROM (
    SELECT
        SUM(CASE WHEN date = CURDATE() THEN 1 ELSE 0 END) AS totalCountToday,
        SUM(CASE WHEN date = CURDATE() - INTERVAL 1 DAY THEN 1 ELSE 0 END) AS totalCountYesterday,
        SUM(CASE WHEN date = CURDATE() AND action = 'deny' THEN 1 ELSE 0 END) AS totalOutgoingToday,
        SUM(CASE WHEN date = CURDATE() - INTERVAL 1 DAY AND action = 'deny' THEN 1 ELSE 0 END) AS totalOutgoingYesterday,
        SUM(CASE WHEN date = CURDATE() AND action = 'accept' THEN 1 ELSE 0 END) AS totalIncomingToday,
        SUM(CASE WHEN date = CURDATE() - INTERVAL 1 DAY AND action = 'accept' THEN 1 ELSE 0 END) AS totalIncomingYesterday,
        SUM(CASE WHEN date = CURDATE() AND subtype = 'login_attempt' THEN 1 ELSE 0 END) AS loginAttemptsToday,
        SUM(CASE WHEN date = CURDATE() - INTERVAL 1 DAY AND subtype = 'login_attempt' THEN 1 ELSE 0 END) AS loginAttemptsYesterday
    FROM logs
) AS daily_counts
    """
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    labels, data_points = get_daily_bandwidth()




    return render_template('home/index.html', segment='index',data=data, labels=json.dumps(labels, default=str), data_points=json.dumps(data_points, default=str))


@blueprint.route('/<template>')
@login_required
def route_template(template):

    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
