from pprint import pformat
import os
import base64
import urllib.parse
import urllib.request
from io import BytesIO
from datetime import datetime, timezone, timedelta
import json
import math

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

GARDENCAM_BUCKET = "gardencam-berrylands-eu-west-1"
GARDENCAM_REGION = "eu-west-1"
GARDENCAM_PARAMETER_NAME = "/berrylands/gardencam/password"
GARDENCAM_PASSWORD = None
GARDENCAM_EARLIEST_IMAGE = "2026-01-19"  # First image: garden_20260119_185439.jpg
TFL_PARAMETER_NAME = "/berrylands/tfl/api-key"
TFL_API_KEY = None
DYNAMODB_TABLE = "cv-access-logs"

# Memspeed configuration - uses same bucket with memspeed/ prefix
MEMSPEED_PREFIX = "memspeed/"
MEMSPEED_RESULTS_PREFIX = "memspeed/results/"
MEMSPEED_DOWNLOADS_PREFIX = "memspeed/downloads/"

# Shared iOS theme CSS + JS — included in every page's <head>
THEME_CSS_JS = '''<script>
(function(){
  var s=localStorage.getItem('theme');
  var p=window.matchMedia('(prefers-color-scheme:dark)').matches;
  document.documentElement.setAttribute('data-theme',s||(p?'dark':'light'));
})();
</script>
<style>
:root{font-size:21px;--bg:#000000;--card-bg:#161616;--text:#E0E0E0;--text-secondary:#8E8E93;--accent:#007AFF;--divider:#2C2C2E;--error:#FF3B30;--warning:#FF9500;--font:-apple-system,'SF Pro Display','Inter','Roboto',sans-serif;}
:root[data-theme="light"]{--bg:#F2F2F7;--card-bg:#FFFFFF;--text:#000000;--text-secondary:#8E8E93;--accent:#007AFF;--divider:#C6C6C8;--error:#FF3B30;--warning:#FF9500;}
#settings-btn{position:fixed;top:0.8rem;right:0.8rem;background:none;border:none;color:var(--text-secondary);font-size:1.2rem;cursor:pointer;z-index:10000;font-family:var(--font);padding:0.3rem;line-height:1;letter-spacing:2px;opacity:0.5;}
#settings-btn:hover{opacity:1;}
#settings-menu{display:none;position:fixed;top:2.4rem;right:0.8rem;background:var(--card-bg);border:1px solid var(--divider);border-radius:10px;padding:0.3rem 0;z-index:10000;min-width:160px;font-family:var(--font);box-shadow:0 4px 12px rgba(0,0,0,0.3);}
#settings-menu.open{display:block;}
.settings-item{display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0.8rem;font-size:0.8rem;color:var(--text);cursor:pointer;white-space:nowrap;}
.settings-item:hover{background:var(--divider);}
.settings-item .check{color:var(--accent);font-size:0.7rem;width:1.2rem;text-align:center;}
</style>
<script>
document.addEventListener('DOMContentLoaded',function(){
  var btn=document.createElement('button');
  btn.id='settings-btn';
  btn.textContent='\u22EF';
  btn.title='Settings';
  var menu=document.createElement('div');
  menu.id='settings-menu';
  // Theme toggle
  var themeItem=document.createElement('div');
  themeItem.className='settings-item';
  var themeLabel=document.createElement('span');
  var themeCheck=document.createElement('span');
  themeCheck.className='check';
  function updateThemeItem(){
    var t=document.documentElement.getAttribute('data-theme');
    themeLabel.textContent=t==='dark'?'Light mode':'Dark mode';
    themeCheck.textContent='';
  }
  updateThemeItem();
  themeItem.appendChild(themeLabel);
  themeItem.appendChild(themeCheck);
  themeItem.onclick=function(e){
    e.stopPropagation();
    var c=document.documentElement.getAttribute('data-theme');
    var n=c==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',n);
    localStorage.setItem('theme',n);
    updateThemeItem();
  };
  menu.appendChild(themeItem);
  // Allow pages to add items
  window._settingsMenu=menu;
  btn.onclick=function(e){e.stopPropagation();menu.classList.toggle('open');};
  document.addEventListener('click',function(){menu.classList.remove('open');});
  document.body.appendChild(btn);
  document.body.appendChild(menu);
});
</script>'''


def format_to_sigfigs(value, sigfigs=3):
    """
    Format a number to specified significant figures, rounding up.

    Args:
        value: The number to format (can be int, float, or Decimal)
        sigfigs: Number of significant figures (default: 3)

    Returns:
        Formatted number as int or float
    """
    # Convert to float (handles Decimal from DynamoDB)
    value = float(value)

    if value == 0:
        return 0

    # Calculate the order of magnitude
    magnitude = math.floor(math.log10(abs(value)))

    # Calculate the scaling factor
    scale = 10 ** (magnitude - sigfigs + 1)

    # Round up using ceiling
    rounded = math.ceil(value / scale) * scale

    # Round to eliminate floating point precision errors
    # Use enough decimal places to preserve significant figures
    decimal_places = max(0, sigfigs - magnitude - 1)
    rounded = round(rounded, decimal_places)

    # Return as int if it's a whole number, otherwise float
    return int(rounded) if rounded == int(rounded) else rounded


def get_parameter(parameter_name):
    """Retrieve a parameter from AWS Systems Manager Parameter Store (FREE!)."""
    if not BOTO3_AVAILABLE:
        print(f"WARNING: boto3 not available. Cannot retrieve parameter: {parameter_name}")
        return None

    try:
        client = boto3.client('ssm', region_name=GARDENCAM_REGION)
        response = client.get_parameter(
            Name=parameter_name,
            WithDecryption=True  # Decrypt SecureString parameters
        )

        value = response['Parameter']['Value']

        # Try to parse as JSON (for structured secrets)
        try:
            data = json.loads(value)
            # If it's a dict with 'password' or 'api_key', extract that
            if isinstance(data, dict):
                return data.get('password') or data.get('api_key') or None
            return value
        except json.JSONDecodeError:
            # Plain string value
            return value

    except Exception as e:
        print(f"ERROR: Failed to retrieve parameter {parameter_name}: {str(e)}")
        return None


# Initialize parameters from Parameter Store on cold start (FREE!)
GARDENCAM_PASSWORD = get_parameter(GARDENCAM_PARAMETER_NAME)
if not GARDENCAM_PASSWORD:
    print(f"WARNING: Could not retrieve password from Parameter Store ({GARDENCAM_PARAMETER_NAME}). Gardencam will be inaccessible.")

SRFCPLUS_COOKIE_PARAM = '/srfcplus/session_cookie'

TFL_API_KEY = get_parameter(TFL_PARAMETER_NAME)
if TFL_API_KEY:
    print("TfL API key loaded from Parameter Store (FREE!)")
else:
    print("WARNING: No TfL API key found. Using unauthenticated access (rate limited).")


def check_basic_auth(event, required_password):
    """Check HTTP Basic Authentication. Returns True if authorized, False otherwise."""
    headers = event.get('headers', {})

    # API Gateway may lowercase headers, so check both cases
    auth_header = headers.get('Authorization') or headers.get('authorization', '')

    if not auth_header.startswith('Basic '):
        return False

    try:
        # Decode base64 credentials
        encoded_credentials = auth_header[6:]  # Remove 'Basic ' prefix
        decoded = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded.split(':', 1)

        # Check password (username can be anything)
        return password == required_password
    except (ValueError, UnicodeDecodeError):
        return False


def log_connection(event, context):
    """Log connection details to DynamoDB."""
    if not BOTO3_AVAILABLE:
        return

    try:
        dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
        table = dynamodb.Table(DYNAMODB_TABLE)

        headers = event.get('headers', {})
        timestamp = datetime.utcnow().isoformat()

        # Get user agent (check both cases due to API Gateway)
        user_agent = headers.get('User-Agent') or headers.get('user-agent', 'Unknown')

        item = {
            'timestamp': timestamp,
            'request_id': context.aws_request_id,
            'path': event.get('path', ''),
            'ip': headers.get('X-Forwarded-For', 'Unknown'),
            'user_agent': user_agent,
            'referer': headers.get('referer') or headers.get('Referer', ''),
            'stage': event.get('requestContext', {}).get('stage', ''),
            'host': headers.get('Host', ''),
            'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())
        }

        table.put_item(Item=item)
    except Exception as e:
        print(f"Failed to log connection: {str(e)}")


def log_execution_metrics(context, duration_ms, path='', ip='', user_agent=''):
    """Log Lambda execution metrics to DynamoDB with IP and User-Agent."""
    if not BOTO3_AVAILABLE:
        return

    try:
        from decimal import Decimal
        dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
        table = dynamodb.Table('lambda-execution-logs')

        timestamp = datetime.utcnow().isoformat()
        function_name = context.function_name

        # Calculate estimated cost (pricing as of 2024)
        # Memory: $0.0000166667 per GB-second
        # Requests: $0.20 per 1M requests
        memory_gb = Decimal(str(context.memory_limit_in_mb)) / Decimal('1024')
        duration_seconds = Decimal(str(duration_ms)) / Decimal('1000')
        memory_cost = memory_gb * duration_seconds * Decimal('0.0000166667')
        request_cost = Decimal('0.0000002')  # $0.20 per 1M requests
        total_cost = memory_cost + request_cost

        item = {
            'function_name': function_name,
            'timestamp': timestamp,
            'request_id': context.aws_request_id,
            'duration_ms': Decimal(str(duration_ms)),
            'memory_limit_mb': Decimal(str(context.memory_limit_in_mb)),
            'path': path,
            'estimated_cost_usd': total_cost,
            'ip_address': ip,
            'user_agent': user_agent,
            'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())
        }

        table.put_item(Item=item)
    except Exception as e:
        print(f"Failed to log execution metrics: {str(e)}")


def parse_timestamp_from_key(key):
    """Extract timestamp from filename: garden_YYYYMMDD_HHMMSS.jpg"""
    try:
        filename_parts = key.replace('.jpg', '').split('_')
        if len(filename_parts) >= 3:
            date_str = filename_parts[1]
            time_str = filename_parts[2]
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
    except:
        pass
    return None


def get_presigned_url(key, expires_in=3600):
    """Generate presigned URL for a specific S3 key."""
    if not BOTO3_AVAILABLE:
        return None
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': GARDENCAM_BUCKET, 'Key': key},
        ExpiresIn=expires_in
    )


def get_images_for_date(date_str):
    """Get gardencam images for a specific date (YYYY-MM-DD).

    Uses S3 prefix filtering for efficiency - only fetches ~240 images instead of all 2,876.
    """
    if not BOTO3_AVAILABLE:
        return []

    # Convert date to S3 prefix: 2026-02-15 → garden_20260215
    date_prefix = f"garden_{date_str.replace('-', '')}"

    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)

    try:
        response = s3.list_objects_v2(
            Bucket=GARDENCAM_BUCKET,
            Prefix=date_prefix,
            MaxKeys=1000  # One day shouldn't have more than 240 images
        )

        if "Contents" not in response:
            return []

        # Convert to standard format with timestamps
        images = []
        for obj in response["Contents"]:
            key = obj["Key"]
            # Skip thumbnails
            if key.startswith('thumb_'):
                continue

            # Extract timestamp from filename: garden_20260215_123456.jpg
            try:
                parts = key.replace('.jpg', '').split('_')
                date_part = parts[1]  # 20260215
                time_part = parts[2]  # 123456

                # Format: YYYY-MM-DD HH:MM:SS
                timestamp = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"

                images.append({
                    'key': key,
                    'timestamp': timestamp,
                    'LastModified': obj['LastModified']
                })
            except:
                pass

        # Sort by timestamp descending
        images.sort(key=lambda x: x['timestamp'], reverse=True)
        return images

    except Exception as e:
        print(f"Error fetching images for date {date_str}: {e}")
        return []


def generate_week_list():
    """Generate list of weeks from GARDENCAM_EARLIEST_IMAGE to today.

    Returns list of week strings in format "2026-W07 (Feb 09-Feb 15)" in reverse chronological order.
    Uses NO S3 queries - purely deterministic date arithmetic.
    """
    from datetime import datetime, timedelta

    # Parse earliest image date
    start_date = datetime.strptime(GARDENCAM_EARLIEST_IMAGE, '%Y-%m-%d')
    end_date = datetime.now()

    weeks = []
    current = end_date

    # Walk backwards from today to start, week by week
    while current >= start_date:
        iso_year, iso_week, iso_weekday = current.isocalendar()

        # Calculate Monday of this week
        days_since_monday = iso_weekday - 1
        monday = current - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)

        # Format: "2026-W07 (Feb 09-Feb 15)"
        week_str = f"{iso_year}-W{iso_week:02d} ({monday.strftime('%b %d')}-{sunday.strftime('%b %d')})"

        if week_str not in weeks:  # Avoid duplicates when scanning
            weeks.append(week_str)

        # Move to previous week
        current = monday - timedelta(days=1)

    return weeks


def get_days_in_week(week_str):
    """Get list of days in a week without loading any images.

    Args:
        week_str: Week string like "2026-W07 (Feb 09-Feb 15)"

    Returns list of day strings in format "2026-02-15 (Sunday)" - NO S3 queries.
    """
    from datetime import datetime, timedelta

    try:
        # Parse week string: "2026-W07 (Feb 09-Feb 15)" → extract dates
        parts = week_str.split(' ')
        year_week = parts[0]  # "2026-W07"
        year = int(year_week.split('-')[0])
        week_num = int(year_week.split('-W')[1])

        # Find Monday of this ISO week
        jan4 = datetime(year, 1, 4)
        week1_monday = jan4 - timedelta(days=jan4.weekday())
        target_monday = week1_monday + timedelta(weeks=week_num - 1)

        # Generate all 7 days (Monday to Sunday)
        days = []
        for day_offset in range(7):
            date = target_monday + timedelta(days=day_offset)
            day_str = date.strftime('%Y-%m-%d (%A)')  # "2026-02-15 (Sunday)"
            days.append(day_str)

        return days

    except Exception as e:
        print(f"Error generating days for week {week_str}: {e}")
        return []


def get_all_gardencam_images(max_keys=None):
    """Get all gardencam images from S3.

    Args:
        max_keys: If provided, only return the N most recent images
    """
    if not BOTO3_AVAILABLE:
        return []
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)

    # Optimization: S3 returns objects in alphabetical order
    # Since our keys are garden_YYYYMMDD_HHMMSS.jpg, alphabetical = chronological
    # We can fetch in reverse by starting from a recent date prefix

    if max_keys and max_keys < 100:
        # Fast path: fetch recent pages only
        # Start from current date and work backwards
        all_objects = []

        # Try last 60 days worth of prefixes
        for days_ago in range(60):
            date = datetime.utcnow() - timedelta(days=days_ago)
            date_prefix = f"garden_{date.strftime('%Y%m%d')}"

            try:
                response = s3.list_objects_v2(
                    Bucket=GARDENCAM_BUCKET,
                    Prefix=date_prefix,
                    MaxKeys=200  # Should cover a full day
                )
                if "Contents" in response:
                    all_objects.extend(response["Contents"])

                # If we have enough, stop searching
                if len(all_objects) >= max_keys * 2:
                    break
            except:
                pass

        # If fast path found nothing, fall back to full scan
        if not all_objects:
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix='garden_')
            for page in pages:
                if "Contents" in page:
                    all_objects.extend(page["Contents"])
    else:
        # Full scan for large requests or galleries
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix='garden_')

        all_objects = []
        for page in pages:
            if "Contents" in page:
                all_objects.extend(page["Contents"])

    if not all_objects:
        return []

    # Sort by Key (filename contains timestamp), newest first
    objects = sorted(all_objects, key=lambda x: x["Key"], reverse=True)
    images = []

    for obj in objects:
        key = obj["Key"]
        # Only include .jpg files
        if not key.endswith('.jpg'):
            continue

        timestamp = parse_timestamp_from_key(key) or obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")

        images.append({
            'key': key,
            'timestamp': timestamp,
            'last_modified': obj["LastModified"]
        })

        # If we have a limit and reached it, stop
        if max_keys and len(images) >= max_keys:
            break

    return images


def get_image_dimensions(s3_client, key):
    """Get image dimensions from S3 object."""
    try:
        from PIL import Image
        from io import BytesIO

        response = s3_client.get_object(Bucket=GARDENCAM_BUCKET, Key=key)
        img = Image.open(BytesIO(response['Body'].read()))
        return img.size  # Returns (width, height)
    except:
        return None


def get_latest_gardencam_images(count=3):
    """Get presigned URLs for the latest N images from S3.

    Optimized version that only fetches what's needed and uses thumbnails.
    Fetches in batches until we have enough displayable images.
    """
    if not BOTO3_AVAILABLE:
        return []

    import time
    t0 = time.time()

    # Fetch images in increasing batch sizes until we have enough displayable ones
    # This handles cases where many images are filtered out
    batch_sizes = [50, 100, 200, 500, 1000]
    images = []
    all_images = []

    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)

    for batch_size in batch_sizes:
        # Fetch images up to this batch size
        t_fetch = time.time()
        all_images = get_all_gardencam_images(max_keys=batch_size)
        print(f"[TIMING] get_all_gardencam_images({batch_size}) took {(time.time()-t_fetch)*1000:.0f}ms, returned {len(all_images)} images")

        # Process and filter images
        t1 = time.time()
        images = []

        for img in all_images:
            # Fetch stats for this image first to check if it should be displayed
            stats = get_image_stats_by_filename(img['key'])

            # Skip images that don't meet display criteria
            if not should_display_image(stats):
                continue

            # Use thumbnail for display (they're pre-generated by gardencam.py)
            # Trust that thumbnails exist - they're created automatically now
            thumb_key = f"thumb_800px_{img['key']}"
            display_url = get_presigned_url(thumb_key)

            # Full-res URL for click-through
            full_url = get_presigned_url(img['key'])

            # Skip resolution lookup - not worth 600ms per page load for cosmetic info
            # Users can see resolution when clicking through to full image

            stats_display = format_stats_for_display(stats)

            images.append({
                'url': display_url,
                'full_url': full_url,
                'timestamp': img['timestamp'],
                'key': img['key'],
                'resolution': '',  # Skipped for performance
                'stats_display': stats_display
            })

            # Stop once we have enough displayable images
            if len(images) >= count:
                break

        print(f"[TIMING] Filtering and URL generation took {(time.time()-t1)*1000:.0f}ms, got {len(images)}/{count} displayable")

        # If we have enough displayable images, we're done
        if len(images) >= count:
            break

        # If we fetched fewer images than requested, we've hit the end of available images
        if len(all_images) < batch_size:
            print(f"[INFO] Only {len(all_images)} images available, {len(images)} displayable")
            break

    print(f"[TIMING] Total get_latest_gardencam_images: {(time.time()-t0)*1000:.0f}ms")

    return images


# ── Springcam ─────────────────────────────────────────────────────────────────

SPRINGCAM_PREFIX = "springcam/"
SPRINGCAM_KEY_PREFIX = "springcam/spring_"


def springcam_thumb_key(key):
    """Convert a springcam image key to its thumbnail key.

    e.g. springcam/spring_20260304_120000.jpg
      -> springcam/thumb_spring_20260304_120000.jpg
    """
    folder, _, basename = key.rpartition('/')
    return f"{folder}/thumb_800px_{basename}"


def get_latest_springcam_images(count=3):
    """Get presigned URLs for the latest N springcam images from S3."""
    if not BOTO3_AVAILABLE:
        return []

    import time
    t0 = time.time()
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    all_objects = []

    # Fast path: try last 60 days by date prefix
    for days_ago in range(60):
        date = datetime.utcnow() - timedelta(days=days_ago)
        prefix = f"springcam/spring_{date.strftime('%Y%m%d')}"
        try:
            response = s3.list_objects_v2(Bucket=GARDENCAM_BUCKET, Prefix=prefix, MaxKeys=100)
            if "Contents" in response:
                all_objects.extend(response["Contents"])
            if len(all_objects) >= count * 2:
                break
        except Exception:
            pass

    # Fall back to full scan if fast path found nothing
    if not all_objects:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=SPRINGCAM_KEY_PREFIX):
            if "Contents" in page:
                all_objects.extend(page["Contents"])

    if not all_objects:
        return []

    objects = sorted(
        [o for o in all_objects if o["Key"].endswith('.jpg')],
        key=lambda x: x["Key"], reverse=True
    )

    images = []
    for obj in objects[:count * 4]:  # a little extra to allow for misses
        key = obj["Key"]
        thumb_key = springcam_thumb_key(key)
        timestamp = parse_timestamp_from_key(key) or obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
        images.append({
            'url': get_presigned_url(thumb_key),
            'full_url': get_presigned_url(key),
            'timestamp': timestamp,
            'key': key,
        })
        if len(images) >= count:
            break

    print(f"[TIMING] get_latest_springcam_images: {(time.time()-t0)*1000:.0f}ms, {len(images)} images")
    return images


def get_all_springcam_images(max_keys=None):
    """Get all springcam images from S3, newest first."""
    if not BOTO3_AVAILABLE:
        return []
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    paginator = s3.get_paginator('list_objects_v2')
    all_objects = []
    for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=SPRINGCAM_KEY_PREFIX):
        if "Contents" in page:
            all_objects.extend(page["Contents"])

    objects = sorted(
        [o for o in all_objects if o["Key"].endswith('.jpg')],
        key=lambda x: x["Key"], reverse=True
    )
    images = []
    for obj in objects:
        key = obj["Key"]
        timestamp = parse_timestamp_from_key(key) or obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
        images.append({'key': key, 'timestamp': timestamp, 'last_modified': obj["LastModified"]})
        if max_keys and len(images) >= max_keys:
            break
    return images


def group_images_by_weeks(images):
    """Group images into weekly periods (Monday-Sunday)."""
    from collections import defaultdict
    from datetime import datetime

    weeks = defaultdict(list)

    for img in images:
        try:
            ts = img['timestamp']
            # Parse timestamp: YYYY-MM-DD HH:MM:SS
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')

            # Get ISO week (returns (year, week_number, weekday))
            iso_year, iso_week, iso_weekday = dt.isocalendar()

            # Calculate Monday of this week
            # ISO weekday: 1=Monday, 7=Sunday
            days_since_monday = iso_weekday - 1
            monday = dt - timedelta(days=days_since_monday)

            # Week key format: "2026-W03 (Jan 13-19)"
            sunday = monday + timedelta(days=6)
            week_key = f"{iso_year}-W{iso_week:02d} ({monday.strftime('%b %d')}-{sunday.strftime('%b %d')})"

            weeks[week_key].append(img)
        except Exception as e:
            weeks['Unknown'].append(img)

    # Sort weeks in reverse chronological order
    sorted_weeks = sorted(weeks.items(), reverse=True)
    return sorted_weeks


def group_images_by_days(images):
    """Group images by individual days."""
    from collections import defaultdict
    from datetime import datetime

    days = defaultdict(list)

    for img in images:
        try:
            ts = img['timestamp']
            # Parse timestamp: YYYY-MM-DD HH:MM:SS
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')

            # Day key format: "2026-02-15 (Saturday)"
            day_key = dt.strftime('%Y-%m-%d (%A)')

            days[day_key].append(img)
        except:
            days['Unknown'].append(img)

    # Sort days in reverse chronological order
    sorted_days = sorted(days.items(), reverse=True)
    return sorted_days


def group_images_by_4hour_periods(images):
    """Group images into 4-hour time periods."""
    from collections import defaultdict

    periods = defaultdict(list)

    for img in images:
        # Parse the timestamp to get the hour
        try:
            ts = img['timestamp']
            # Format: YYYY-MM-DD HH:MM:SS
            date_part = ts.split()[0]
            hour = int(ts.split()[1].split(':')[0])

            # Calculate 4-hour period (0-3, 4-7, 8-11, 12-15, 16-19, 20-23)
            period_start = (hour // 4) * 4
            period_key = f"{date_part} {period_start:02d}:00-{(period_start+3):02d}:59"

            periods[period_key].append(img)
        except:
            periods['Unknown'].append(img)

    # Sort periods in reverse chronological order
    sorted_periods = sorted(periods.items(), reverse=True)
    return sorted_periods


def get_gardencam_stats(limit=500):
    """Get image statistics from DynamoDB."""
    if not BOTO3_AVAILABLE:
        return []

    try:
        dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
        table = dynamodb.Table('gardencam-stats')

        response = table.scan(Limit=limit)
        items = response.get('Items', [])

        # Sort by timestamp
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return items
    except Exception as e:
        print(f"Error fetching stats from DynamoDB: {e}")
        return []


def get_image_stats_by_filename(filename):
    """Get statistics for a specific image from DynamoDB."""
    if not BOTO3_AVAILABLE:
        return None

    try:
        # Extract just the filename without path
        if '/' in filename:
            filename = filename.split('/')[-1]
        # Remove thumb_ prefix if present
        if filename.startswith('thumb_'):
            filename = filename[6:]

        dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
        table = dynamodb.Table('gardencam-stats')

        response = table.get_item(Key={'filename': filename})
        return response.get('Item')
    except Exception as e:
        print(f"Error fetching stats for {filename}: {e}")
        return None


def should_display_image(stats):
    """Check if image should be displayed (filter out redundant bright daytime images)."""
    if not stats:
        return True  # Show images without stats

    brightness = float(stats.get('avg_brightness', 0))
    diff = float(stats.get('image_diff', 0))

    # Hide images with high brightness and low change (same criteria as capture script)
    # Only filter when diff was actually measured (> 0); diff == 0 means not calculated
    if brightness > 100 and 0 < diff < 15:
        return False

    return True


def calculate_time_delta(current_timestamp, previous_timestamp):
    """Calculate time delta between two timestamps and format as string.

    Returns string like "+2m", "+15m", "+1h 5m", etc.
    Returns empty string if calculation fails.
    """
    if not current_timestamp or not previous_timestamp:
        return ""

    try:
        # Parse timestamps - handle both "YYYY-MM-DD HH:MM:SS" and "HH:MM:SS" formats
        from datetime import datetime

        # If timestamps have dates, parse full format
        if ' ' in current_timestamp and len(current_timestamp) > 10:
            current_dt = datetime.strptime(current_timestamp, "%Y-%m-%d %H:%M:%S")
            previous_dt = datetime.strptime(previous_timestamp, "%Y-%m-%d %H:%M:%S")
        else:
            # Time-only format - assume same day
            current_dt = datetime.strptime(current_timestamp, "%H:%M:%S")
            previous_dt = datetime.strptime(previous_timestamp, "%H:%M:%S")

        # Calculate delta (previous is later/more recent, current is earlier in the list)
        # So we want previous - current to get the time gap
        delta_seconds = abs((previous_dt - current_dt).total_seconds())

        # Format delta
        minutes = int(delta_seconds / 60)
        hours = minutes // 60
        remaining_minutes = minutes % 60

        if hours > 0:
            if remaining_minutes > 0:
                return f"+{hours}h {remaining_minutes}m"
            else:
                return f"+{hours}h"
        elif minutes > 0:
            return f"+{minutes}m"
        else:
            return "+<1m"

    except Exception as e:
        print(f"Error calculating time delta: {e}")
        return ""


def format_stats_for_display(stats):
    """Format brightness, image diff, and SD for display with 3 significant figures."""
    if not stats:
        return ""

    brightness = float(stats.get('avg_brightness', 0))
    # Use image_diff (difference from previous image)
    diff = float(stats.get('image_diff', 0))
    # Use noise_floor as standard deviation
    sd = float(stats.get('noise_floor', 0))

    # Format to 3 significant figures
    from decimal import Decimal

    def format_sig_figs(value, sig_figs=3):
        if value == 0:
            return "0.00"
        d = Decimal(str(value))
        return f"{d:.{sig_figs}g}"

    brightness_str = format_sig_figs(brightness)
    diff_str = format_sig_figs(diff)
    sd_str = format_sig_figs(sd)

    return f" | B:{brightness_str} Δ:{diff_str} SD:{sd_str}"


def get_all_lambda_functions():
    """Get list of all Lambda functions with memory sizes."""
    if not BOTO3_AVAILABLE:
        return {}

    try:
        lambda_client = boto3.client('lambda', region_name=GARDENCAM_REGION)
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])
        return {f['FunctionName']: {'memory_mb': f.get('MemorySize', 128)} for f in functions}
    except Exception as e:
        print(f"Error listing Lambda functions: {e}")
        return {}


def get_cloudwatch_metrics(function_name, days=30):
    """Get CloudWatch metrics for Lambda function."""
    if not BOTO3_AVAILABLE:
        return {}

    try:
        cloudwatch = boto3.client('cloudwatch', region_name=GARDENCAM_REGION)

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        metrics = {}

        # Get invocations
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Invocations',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        metrics['invocations'] = response.get('Datapoints', [])

        # Get errors
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Errors',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=['Sum']
        )
        metrics['errors'] = response.get('Datapoints', [])

        # Get throttles
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Throttles',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=['Sum']
        )
        metrics['throttles'] = response.get('Datapoints', [])

        # Get duration
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Duration',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=['Average', 'Maximum']
        )
        metrics['duration'] = response.get('Datapoints', [])

        return metrics
    except Exception as e:
        print(f"Error fetching CloudWatch metrics: {e}")
        return {}


def get_all_lambda_metrics(days=30):
    """Get CloudWatch metrics for all Lambda functions."""
    functions = get_all_lambda_functions()
    print(f"Found {len(functions)} Lambda functions: {list(functions.keys())}")
    all_metrics = {}

    for func_name, func_info in functions.items():
        metrics = get_cloudwatch_metrics(func_name, days)
        print(f"Metrics for {func_name}: {len(metrics)} metric types")
        if metrics:
            # Calculate totals
            total_invocations = sum(dp.get('Sum', 0) for dp in metrics.get('invocations', []))
            total_errors = sum(dp.get('Sum', 0) for dp in metrics.get('errors', []))
            total_throttles = sum(dp.get('Sum', 0) for dp in metrics.get('throttles', []))

            durations = [dp.get('Average', 0) for dp in metrics.get('duration', []) if dp.get('Average')]
            maxes = [dp.get('Maximum', 0) for dp in metrics.get('duration', []) if dp.get('Maximum')]

            avg_duration = sum(durations) / len(durations) if durations else 0
            max_duration = max(maxes) if maxes else 0
            error_rate = (total_errors / total_invocations * 100) if total_invocations > 0 else 0

            # GB-seconds: (memory_mb / 1024) * total_duration_seconds
            # avg_duration is ms, multiply by invocations to get total ms
            memory_gb = func_info['memory_mb'] / 1024
            total_duration_s = (avg_duration * total_invocations) / 1000
            gb_seconds = memory_gb * total_duration_s

            all_metrics[func_name] = {
                'invocations': total_invocations,
                'errors': total_errors,
                'throttles': total_throttles,
                'avg_duration': avg_duration,
                'max_duration': max_duration,
                'error_rate': error_rate,
                'memory_mb': func_info['memory_mb'],
                'gb_seconds': gb_seconds,
                'raw_metrics': metrics
            }

    return all_metrics


def categorize_path(path):
    """Categorize path into application."""
    if not path or path == '/':
        return 'root'

    path = path.lower()

    if 'gardencam' in path:
        return 'gardencam'
    elif 't3' in path or 'parklands' in path or 'surbiton' in path:
        return 't3-bus'
    elif 'lambda-stats' in path:
        return 'lambda-stats'
    elif 'memspeed' in path:
        return 'memspeed'
    elif 'contents' in path:
        return 'contents'
    elif 'gitinfo' in path:
        return 'gitinfo'
    elif 'event' in path:
        return 'debug'
    else:
        return 'other'


def get_ip_geolocation(ip_address):
    """Get geolocation data for an IP address using ip-api.com (free, no key needed)."""
    if not ip_address or ip_address == 'Unknown':
        return {'country': 'Unknown', 'city': 'Unknown', 'lat': 0, 'lon': 0}

    # Handle multiple IPs in X-Forwarded-For (take first one)
    if ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    try:
        import urllib.request
        import json

        url = f'http://ip-api.com/json/{ip_address}?fields=status,country,city,lat,lon'
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())

            if data.get('status') == 'success':
                return {
                    'country': data.get('country', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'lat': data.get('lat', 0),
                    'lon': data.get('lon', 0)
                }
    except Exception as e:
        print(f"Error getting geolocation for {ip_address}: {e}")

    return {'country': 'Unknown', 'city': 'Unknown', 'lat': 0, 'lon': 0}


def get_lambda_execution_stats(days=30):
    """Get Lambda execution statistics from DynamoDB for the last N days.

    Uses query (not scan) against known partition keys with a timestamp range,
    since the table has function_name (HASH) and timestamp (RANGE).
    """
    if not BOTO3_AVAILABLE:
        return []

    try:
        from boto3.dynamodb.conditions import Key

        dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
        table = dynamodb.Table('lambda-execution-logs')

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + 'Z'
        partition_keys = ['mywebsite-local', 'cvdev']

        items = []
        for pk in partition_keys:
            response = table.query(
                KeyConditionExpression=Key('function_name').eq(pk) & Key('timestamp').gte(cutoff)
            )
            items.extend(response.get('Items', []))

            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=Key('function_name').eq(pk) & Key('timestamp').gte(cutoff),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))

        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return items
    except Exception as e:
        print(f"Error fetching Lambda execution stats from DynamoDB: {e}")
        return []


# ============================================================================
# Pi Fleet Status Dashboard
# ============================================================================

def get_pi_fleet_status():
    """Get Pi fleet status from DynamoDB."""
    if not BOTO3_AVAILABLE:
        return []

    try:
        dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
        table = dynamodb.Table('pi-fleet-status')

        response = table.scan()
        items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        # Sort by hostname
        items.sort(key=lambda x: x.get('hostname', ''))

        return items
    except Exception as e:
        print(f"Error fetching pi-fleet status from DynamoDB: {e}")
        return []


def format_uptime(seconds):
    """Format uptime in a human-readable way."""
    if not seconds:
        return "Unknown"

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or not parts:
        parts.append(f"{minutes}m")

    return " ".join(parts)


def format_age(last_seen):
    """Return human-readable age string for a timestamp, e.g. '2 minutes ago'."""
    if not last_seen or last_seen == 'Never':
        return 'Never'
    try:
        from dateutil import parser as dtparser
        last_seen_dt = dtparser.parse(last_seen)
    except Exception:
        try:
            last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
        except Exception:
            return last_seen
    now = datetime.now(timezone.utc)
    delta = int((now - last_seen_dt).total_seconds())
    if delta < 60:
        return f"{delta}s ago"
    elif delta < 3600:
        m = delta // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    elif delta < 86400:
        h = delta // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    else:
        d = delta // 86400
        return f"{d} day{'s' if d != 1 else ''} ago"


def is_pi_online(last_seen):
    """Check if Pi is online based on last_seen timestamp."""
    if not last_seen:
        return False

    try:
        from dateutil import parser
        last_seen_dt = parser.parse(last_seen)
    except:
        try:
            last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
        except:
            return False

    # Consider online if seen in last 2 minutes
    now = datetime.now(timezone.utc)
    delta = (now - last_seen_dt).total_seconds()
    return delta < 120


def render_pi_fleet_page(pis):
    """Render the Pi Fleet dashboard HTML."""

    # Count online/offline
    online_count = sum(1 for pi in pis if is_pi_online(pi.get('last_seen')))
    offline_count = len(pis) - online_count

    html = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pi Fleet Status</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMiAzMiI+CiAgPCEtLSBCbHVlIFBldGVyIG5hdXRpY2FsIGZsYWcgLS0+CiAgPHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiBmaWxsPSIjMDAzODkzIiByeD0iMyIvPgogIDxyZWN0IHg9IjkiIHk9IjkiIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgZmlsbD0iI0ZGRkZGRiIvPgo8L3N2Zz4K">
    <style>
        body {{ font-family: var(--font); background: var(--bg); color: var(--text); min-height: 100vh; margin: 0; padding: 2rem; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: var(--text); text-align: center; margin-bottom: 2rem; }}
        .home-link {{ text-align: center; margin-bottom: 1rem; }}
        .home-link a {{ color: var(--accent); text-decoration: none; font-size: 1rem; }}
        .home-link a:hover {{ opacity: 0.8; }}
        .summary {{ background: var(--card-bg); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; border: 1px solid var(--divider); display: flex; justify-content: space-around; flex-wrap: wrap; gap: 1rem; }}
        .summary-item {{ text-align: center; }}
        .summary-value {{ font-size: 2rem; font-weight: bold; margin-bottom: 0.25rem; }}
        .summary-label {{ color: var(--text-secondary); font-size: 0.9rem; }}
        .online {{ color: #10b981; }}
        .offline {{ color: var(--error); }}
        .total {{ color: var(--accent); }}
        .pi-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }}
        .pi-card {{ background: var(--card-bg); border-radius: 12px; padding: 1rem; border: 1px solid var(--divider); transition: opacity 0.2s; }}
        .pi-card:hover {{ opacity: 0.9; }}
        .pi-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--divider); }}
        .pi-hostname {{ font-size: 1.1rem; font-weight: bold; color: var(--text); }}
        .pi-status {{ font-size: 0.8rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 10px; }}
        .status-online {{ background: rgba(16,185,129,0.2); color: #10b981; }}
        .status-offline {{ background: rgba(255,59,48,0.2); color: var(--error); }}
        .pi-info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.75rem; }}
        .info-item {{ font-size: 0.8rem; }}
        .info-label {{ color: var(--text-secondary); font-weight: 500; font-size: 0.75rem; }}
        .info-value {{ color: var(--text); font-weight: 600; }}
        .metrics {{ display: flex; gap: 0.75rem; margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--divider); }}
        .metric {{ flex: 1; text-align: center; }}
        .metric-value {{ font-size: 1.2rem; font-weight: bold; color: var(--accent); }}
        .metric-label {{ font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; }}
        .boot-progress {{ margin-top: 1rem; padding: 0.75rem; background: rgba(255,149,0,0.15); border-left: 4px solid var(--warning); border-radius: 4px; font-size: 0.85rem; color: var(--text); }}
        .error-box {{ margin-top: 1rem; padding: 0.75rem; background: rgba(255,59,48,0.15); border-left: 4px solid var(--error); border-radius: 4px; font-size: 0.85rem; color: var(--error); }}
        .empty-state {{ background: var(--card-bg); border-radius: 12px; padding: 3rem; text-align: center; border: 1px solid var(--divider); }}
        .empty-state h2 {{ color: var(--text-secondary); }}
        .auto-refresh {{ text-align: center; color: var(--text-secondary); margin-top: 2rem; font-size: 0.9rem; }}
        @media (max-width: 768px) {{ .pi-grid {{ grid-template-columns: 1fr; }} .pi-info {{ grid-template-columns: 1fr; }} }}
    </style>
    {THEME_CSS_JS}
    </head>
    <body>
    <div class="container">
        <div class="home-link">
            <a href="contents">← Home</a>
        </div>

        <h1>Pi Fleet Status</h1>
    '''

    html += f'''
        <div class="summary">
            <div class="summary-item">
                <div class="summary-value online">{online_count}</div>
                <div class="summary-label">Online</div>
            </div>
            <div class="summary-item">
                <div class="summary-value offline">{offline_count}</div>
                <div class="summary-label">Offline</div>
            </div>
            <div class="summary-item">
                <div class="summary-value total">{len(pis)}</div>
                <div class="summary-label">Total Devices</div>
            </div>
        </div>
    '''

    if not pis:
        html += '''
        <div class="empty-state">
            <h2>No Devices Found</h2>
            <p>No Raspberry Pis have reported their status yet.</p>
            <p>Make sure the pi-fleet-reporter service is running on your devices.</p>
        </div>
        '''
    else:
        html += '<div class="pi-grid">'

        for pi in pis:
            hostname = pi.get('hostname', 'unknown')
            online = is_pi_online(pi.get('last_seen'))
            status_class = 'status-online' if online else 'status-offline'
            status_text = 'Online' if online else 'Offline'

            # Card ID: Use card_id if set, otherwise last 4 digits of SD CID
            card_id = pi.get('card_id', 'unknown')
            if card_id == 'unknown' or not card_id:
                sd_cid = pi.get('sd_cid', '')
                if sd_cid and len(sd_cid) >= 4:
                    card_id = sd_cid[-4:]  # Last 4 hex digits
                else:
                    card_id = 'unknown'

            serial = pi.get('serial', 'unknown')  # Keep for backward compatibility
            local_ip = pi.get('local_ip', 'unknown')
            app_name = pi.get('app_name', 'unknown')
            if app_name == 'unknown':
                app_name = pi.get('expected_app', 'unknown')
            uptime = format_uptime(pi.get('uptime_seconds', 0))

            cpu = pi.get('cpu_percent', 0)
            mem = pi.get('memory_percent', 0)
            disk = pi.get('disk_percent', 0)

            # Format memory with total - 3 sig figs, rounded up
            # Use MB for < 1024 MB, otherwise GB
            mem_total_mb = pi.get('memory_total_mb', 0)
            if mem_total_mb > 0:
                if mem_total_mb < 1024:
                    # Display in MB for values < 1GB
                    mem_total_formatted = format_to_sigfigs(mem_total_mb, 3)
                    if isinstance(mem_total_formatted, float) and mem_total_formatted.is_integer():
                        mem_total_formatted = int(mem_total_formatted)
                    mem_display = f"{mem}%<br><span style='font-size: 0.7em; opacity: 0.8;'>of {mem_total_formatted}M</span>"
                else:
                    # Display in GB for values >= 1GB
                    mem_total_gb = mem_total_mb / 1024
                    mem_total_formatted = format_to_sigfigs(mem_total_gb, 3)
                    if isinstance(mem_total_formatted, float) and mem_total_formatted.is_integer():
                        mem_total_formatted = int(mem_total_formatted)
                    mem_display = f"{mem}%<br><span style='font-size: 0.7em; opacity: 0.8;'>of {mem_total_formatted}G</span>"
            else:
                mem_display = f"{mem}%"

            # Format disk with total - 3 sig figs, rounded up
            # Use MB for < 1 GB, otherwise GB
            disk_total_gb = pi.get('disk_total_gb', 0)
            if disk_total_gb > 0:
                if disk_total_gb < 1:
                    # Display in MB for values < 1GB
                    disk_total_mb = disk_total_gb * 1024
                    disk_total_formatted = format_to_sigfigs(disk_total_mb, 3)
                    if isinstance(disk_total_formatted, float) and disk_total_formatted.is_integer():
                        disk_total_formatted = int(disk_total_formatted)
                    disk_display = f"{disk}%<br><span style='font-size: 0.7em; opacity: 0.8;'>of {disk_total_formatted}M</span>"
                else:
                    # Display in GB for values >= 1GB
                    disk_total_formatted = format_to_sigfigs(disk_total_gb, 3)
                    if isinstance(disk_total_formatted, float) and disk_total_formatted.is_integer():
                        disk_total_formatted = int(disk_total_formatted)
                    disk_display = f"{disk}%<br><span style='font-size: 0.7em; opacity: 0.8;'>of {disk_total_formatted}G</span>"
            else:
                disk_display = f"{disk}%"

            tunnel_active = pi.get('tunnel_active', False)
            tunnel_port = pi.get('tunnel_port', 0)
            bastion_host = pi.get('bastion_host', 'unknown')

            last_seen = pi.get('last_seen', 'Never')
            last_seen_str = format_age(last_seen)

            html += f'''
            <div class="pi-card">
                <div class="pi-header">
                    <div class="pi-hostname">{hostname}</div>
                    <div class="pi-status {status_class}">{status_text}</div>
                </div>

                <div class="pi-info">
                    <div class="info-item">
                        <div class="info-label">Model</div>
                        <div class="info-value" style="font-size: 0.75em;">{pi.get('cpu_model', 'Unknown')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Card ID</div>
                        <div class="info-value">{card_id}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Local IP</div>
                        <div class="info-value">{local_ip}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">App</div>
                        <div class="info-value">{app_name}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Uptime</div>
                        <div class="info-value">{uptime}</div>
                    </div>
                    <div class="info-item" style="grid-column: 1 / -1;">
                        <div class="info-label">OS</div>
                        <div class="info-value" style="font-size: 0.75em;">{pi.get('os_version', 'Unknown')}</div>
                    </div>
            '''

            if pi.get('wifi_interface'):
                html += f'''
                    <div class="info-item" style="grid-column: 1 / -1;">
                        <div class="info-label">WiFi</div>
                        <div class="info-value" style="font-size: 0.75em;">{pi.get('wifi_interface')}</div>
                    </div>
                '''

            if tunnel_active:
                html += f'''
                    <div class="info-item">
                        <div class="info-label">SSH Tunnel</div>
                        <div class="info-value">Port {tunnel_port}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Bastion</div>
                        <div class="info-value">{bastion_host}</div>
                    </div>
                '''

            html += f'''
                    <div class="info-item" style="grid-column: 1 / -1;">
                        <div class="info-label">Last Seen</div>
                        <div class="info-value">{last_seen_str}</div>
                    </div>
                </div>
            '''

            if online:
                html += f'''
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">{cpu}%</div>
                        <div class="metric-label">CPU</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{mem_display}</div>
                        <div class="metric-label">Memory</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{disk_display}</div>
                        <div class="metric-label">Disk</div>
                    </div>
                </div>
                '''

            # Show boot progress if in provisioning
            boot_progress = pi.get('boot_progress') or pi.get('stage')
            if boot_progress and boot_progress.startswith('boot'):
                message = pi.get('message', 'Provisioning in progress...')
                html += f'''
                <div class="boot-progress">
                    <strong>🔄 Boot Progress:</strong> {boot_progress}<br>
                    {message}
                </div>
                '''

            # Show error if present
            error = pi.get('error')
            if error:
                html += f'''
                <div class="error-box">
                    <strong>⚠️ Error:</strong><br>
                    {error[:200]}{'...' if len(error) > 200 else ''}
                </div>
                '''

            html += '</div>'

        html += '</div>'

    html += '''
        <div class="auto-refresh">
            Page auto-refreshes every 30 seconds • <span id="countdown">refreshing in 30 seconds</span>
        </div>
    </div>

    <script>
        // Auto-refresh with countdown
        let secondsLeft = 30;
        const countdownEl = document.getElementById('countdown');

        function updateCountdown() {
            countdownEl.textContent = `refreshing in ${secondsLeft} second${secondsLeft !== 1 ? 's' : ''}`;
            secondsLeft--;

            if (secondsLeft < 0) {
                location.reload();
            }
        }

        // Update immediately
        updateCountdown();

        // Update every second
        setInterval(updateCountdown, 1000);
    </script>
    </body>
    </html>
    '''

    return html


# ============================================================================
# t3 - Terse Transport Times (Parklands stop, K2 bus)
# ============================================================================

TFL_API_BASE = "https://api.tfl.gov.uk"
T3_BUSES_PER_DIRECTION = 2

# Stop configurations for K2 bus
T3_STOPS = {
    'parklands': {
        'name': 'Parklands',
        'inbound': '490010781S',   # Parklands southbound (towards Kingston)
        'outbound': '490010781N',  # Parklands northbound (towards Hook)
        'inbound_dest': 'Kingston',
        'outbound_dest': 'Hook'
    },
    'surbiton': {
        'name': 'Surbiton Station',
        'outbound': '490015165B',  # Surbiton Station towards Hook
        'outbound_dest': 'Hook'
        # No inbound - only show outbound at Surbiton
    }
}

# Legacy constants for backwards compatibility
T3_STOP_INBOUND = T3_STOPS['parklands']['inbound']
T3_STOP_OUTBOUND = T3_STOPS['parklands']['outbound']

# In-Lambda cache: {stop_id: (timestamp, data)} — avoids hitting TfL more than once per TTL
_t3_cache = {}
T3_CACHE_TTL = 30  # seconds


def t3_fetch_stop(stop_id, api_key=None):
    """Fetch arrivals for a specific stop. Returns seconds. Caches for T3_CACHE_TTL seconds."""
    import time
    now = time.time()
    if stop_id in _t3_cache:
        ts, cached = _t3_cache[stop_id]
        if now - ts < T3_CACHE_TTL:
            return cached, None

    url = f"{TFL_API_BASE}/StopPoint/{stop_id}/Arrivals"
    if api_key:
        url += f"?app_key={api_key}"

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 't3-terse-transport-times/1.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        result = [a.get('timeToStation', 0) for a in data]
        _t3_cache[stop_id] = (now, result)
        return result, None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
        except Exception:
            body = ''
        return [], f"HTTP {e.code}: {body or e.reason}"
    except Exception as e:
        return [], str(e)


def t3_seconds_to_quarter_minutes(seconds):
    """Convert seconds to quarter-minute string (e.g., 5, 5¼, 5½, 5¾)."""
    minutes = seconds // 60
    remainder = seconds % 60
    if remainder < 15:
        return str(minutes)
    elif remainder < 30:
        return f"{minutes}¼"
    elif remainder < 45:
        return f"{minutes}½"
    else:
        return f"{minutes}¾"


def t3_fetch_arrivals(api_key=None, stop='parklands'):
    """Fetch bus arrivals for specified stop from TfL API."""
    stop_config = T3_STOPS.get(stop, T3_STOPS['parklands'])

    result = {}
    errors = []

    # Fetch inbound if available for this stop
    if 'inbound' in stop_config:
        inbound, err = t3_fetch_stop(stop_config['inbound'], api_key)
        if err:
            errors.append(err)
        else:
            inbound.sort()
            result['inbound'] = inbound[:T3_BUSES_PER_DIRECTION]

    # Fetch outbound if available for this stop
    if 'outbound' in stop_config:
        outbound, err = t3_fetch_stop(stop_config['outbound'], api_key)
        if err:
            errors.append(err)
        else:
            outbound.sort()
            result['outbound'] = outbound[:T3_BUSES_PER_DIRECTION]

    if not result and errors:
        return {}, '; '.join(errors)

    return result, None


def t3_format_html(arrivals):
    """Format Parklands arrivals as HTML."""
    inbound = arrivals.get('inbound', [])
    outbound = arrivals.get('outbound', [])

    def format_times(times):
        if not times:
            return '<span class="time-box" style="color:#666">--</span>'
        boxes = []
        for i, secs in enumerate(times):
            cls = 'time-box next' if i == 0 else 'time-box'
            display = t3_seconds_to_quarter_minutes(secs)
            boxes.append(f'<span class="{cls}">{display}</span>')
        return ' '.join(boxes)

    return f"""{THEME_CSS_JS}
<title>K2 Parklands</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html {{ font-size: 16px; }}
body {{ font-family: var(--font); background: var(--bg); color: var(--text); padding: 1rem; margin: 0; text-align: center; }}
.nav {{ position: absolute; top: 1rem; left: 1rem; }}
.nav a {{ color: var(--accent); text-decoration: none; font-size: 0.9rem; }}
h1 {{ font-size: 1.2rem; margin-top: 1rem; margin-bottom: 6rem; }}
.direction {{ margin: 3rem 0; }}
.times {{ font-family: monospace; }}
.time-box {{ display: inline-block; font-size: 6rem; color: var(--accent); border: 2px solid var(--accent); border-radius: 12px; padding: 0.3rem 0.8rem; margin: 0 0.5rem; }}
.time-box.next {{ color: var(--text); font-weight: bold; border-color: var(--text); }}
.dest {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 1rem; }}
.refresh {{ font-size: 0.8rem; color: var(--text-secondary); margin-top: 3rem; }}
</style>
<div class="nav"><a href="contents">Home</a></div>
<h1>K2 @ Parklands</h1>
<div class="direction">
  <div class="times">{format_times(inbound)}</div>
  <div class="dest">towards Kingston</div>
</div>
<div class="direction">
  <div class="times">{format_times(outbound)}</div>
  <div class="dest">towards Hook</div>
</div>
<div class="refresh">refresh in <span id="countdown">60</span>s</div>
<script>
let t = 60;
const el = document.getElementById('countdown');
setInterval(() => {{
  t--;
  if (t <= 0) location.reload();
  el.textContent = t;
}}, 1000);
</script>
"""


def t3_format_json(arrivals, stop='parklands'):
    """Format arrivals as JSON for API consumers."""
    stop_config = T3_STOPS.get(stop, T3_STOPS['parklands'])

    result = {
        "stop": stop_config['name'],
        "route": "K2",
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    # Add inbound if available for this stop
    if 'inbound' in stop_config:
        result["inbound"] = {
            "destination": stop_config['inbound_dest'],
            "seconds": arrivals.get('inbound', [])
        }

    # Add outbound if available for this stop
    if 'outbound' in stop_config:
        result["outbound"] = {
            "destination": stop_config['outbound_dest'],
            "seconds": arrivals.get('outbound', [])
        }

    return json.dumps(result)


# ============================================================================
# Memspeed - Memory bandwidth benchmark visualization
# ============================================================================

def get_memspeed_results():
    """Get all memspeed benchmark results from S3."""
    if not BOTO3_AVAILABLE:
        return []

    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    results = []

    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=MEMSPEED_RESULTS_PREFIX):
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                key = obj["Key"]
                if not key.endswith('.json'):
                    continue
                try:
                    response = s3.get_object(Bucket=GARDENCAM_BUCKET, Key=key)
                    data = json.loads(response['Body'].read().decode('utf-8'))
                    data['_key'] = key
                    results.append(data)
                except Exception as e:
                    print(f"Error reading {key}: {e}")
    except Exception as e:
        print(f"Error listing memspeed results: {e}")

    return results


def get_memspeed_downloads():
    """Get list of available memspeed downloads from S3."""
    if not BOTO3_AVAILABLE:
        return []

    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    downloads = []

    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=MEMSPEED_DOWNLOADS_PREFIX):
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                key = obj["Key"]
                filename = key.replace(MEMSPEED_DOWNLOADS_PREFIX, '')
                if not filename:
                    continue
                downloads.append({
                    'key': key,
                    'filename': filename,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
    except Exception as e:
        print(f"Error listing memspeed downloads: {e}")

    return downloads


def get_memspeed_download_url(key, expires_in=3600):
    """Generate presigned URL for a memspeed download."""
    if not BOTO3_AVAILABLE:
        return None
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': GARDENCAM_BUCKET, 'Key': key},
        ExpiresIn=expires_in
    )


def save_memspeed_result(data):
    """Save a memspeed benchmark result to S3."""
    if not BOTO3_AVAILABLE:
        return False, "S3 not available"

    # Validate required fields
    required = ['machine', 'data']
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Add timestamp if not present
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Generate key from machine name and timestamp
    machine = data['machine'].replace(' ', '_').replace('/', '_')
    ts = data['timestamp'].replace(':', '-').replace('T', '_').split('.')[0]
    key = f"{MEMSPEED_RESULTS_PREFIX}{machine}_{ts}.json"

    try:
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        s3.put_object(
            Bucket=GARDENCAM_BUCKET,
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
        return True, key
    except Exception as e:
        return False, str(e)


def render_memspeed_page(results, downloads):
    """Render the memspeed visualization page."""
    # Assign colors to machines
    colors = [
        '#4a9eff', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
    ]

    # Prepare datasets for Chart.js
    datasets_js = []
    for i, result in enumerate(results):
        machine = result.get('machine', 'Unknown')
        color = colors[i % len(colors)]
        data_points = result.get('data', [])

        # Format data for scatter plot
        points = [{'x': p['size'], 'y': p['speed']} for p in data_points]

        cpu = result.get('cpu', '')
        ram = result.get('ram', '')
        label = machine
        if cpu:
            label += f" ({cpu})"

        datasets_js.append({
            'label': label,
            'data': points,
            'borderColor': color,
            'backgroundColor': color,
            'showLine': True,
            'tension': 0.1,
            'pointRadius': 2,
            'borderWidth': 2
        })

    # Build downloads HTML
    downloads_html = ''
    if downloads:
        downloads_html = '<h2>Downloads</h2><div class="downloads-grid">'
        for dl in downloads:
            size_kb = dl['size'] / 1024
            if size_kb > 1024:
                size_str = f"{size_kb/1024:.1f} MB"
            else:
                size_str = f"{size_kb:.1f} KB"
            downloads_html += f'''
            <a href="memspeed/download?file={dl['filename']}" class="download-item">
                <span class="filename">{dl['filename']}</span>
                <span class="filesize">{size_str}</span>
            </a>
            '''
        downloads_html += '</div>'

    # Build results table
    results_table = ''
    if results:
        results_table = '''
        <h2>Benchmark Results</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Machine</th>
                    <th>CPU</th>
                    <th>Cache (L1 / L2 / L3)</th>
                    <th>RAM</th>
                    <th>OS</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
        '''
        for result in results:
            cache = result.get('cache', {})
            if cache:
                cache_str = f"{cache.get('L1', '-')} / {cache.get('L2', '-')} / {cache.get('L3', '-')}"
            else:
                cache_str = '-'
            results_table += f'''
                <tr>
                    <td>{result.get('machine', 'Unknown')}</td>
                    <td>{result.get('cpu', '-')}</td>
                    <td>{cache_str}</td>
                    <td>{result.get('ram', '-')}</td>
                    <td>{result.get('os', '-')}</td>
                    <td>{result.get('timestamp', '-')}</td>
                </tr>
            '''
        results_table += '</tbody></table>'

    return f'''{THEME_CSS_JS}
    <title>Memory Bandwidth Benchmark</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{ font-family: var(--font); margin: 0; padding: 1rem; background: var(--bg); color: var(--text); }}
        .nav {{ text-align: center; margin-bottom: 1.5rem; }}
        .nav a {{ color: var(--accent); text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 6px; display: inline-block; }}
        .nav a:hover {{ opacity: 0.8; }}
        h1 {{ text-align: center; margin-bottom: 2rem; }}
        h2 {{ color: var(--text-secondary); margin-top: 2rem; }}
        .chart-container {{ max-width: 1400px; margin: 0 auto 2rem auto; background: var(--card-bg); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--divider); }}
        .chart-title {{ font-size: 1.2rem; margin-bottom: 1rem; color: var(--text-secondary); text-align: center; }}
        canvas {{ max-height: 500px; }}
        .upload-section {{ max-width: 600px; margin: 2rem auto; padding: 1.5rem; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 8px; }}
        .upload-section h2 {{ margin-top: 0; }}
        .upload-form {{ display: flex; flex-direction: column; gap: 1rem; }}
        .upload-form input[type="file"] {{ padding: 0.5rem; background: var(--bg); border: 1px solid var(--divider); border-radius: 4px; color: var(--text); }}
        .upload-form button {{ padding: 0.75rem 1.5rem; background: var(--accent); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; }}
        .upload-form button:hover {{ opacity: 0.85; }}
        .upload-form button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        #uploadStatus {{ margin-top: 0.5rem; font-size: 0.9rem; }}
        .downloads-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; margin-top: 1rem; }}
        .download-item {{ display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: var(--card-bg); border-radius: 6px; text-decoration: none; color: var(--accent); border: 1px solid var(--divider); transition: background 0.2s; }}
        .download-item:hover {{ background: rgba(142,142,147,0.1); }}
        .filename {{ font-family: monospace; }}
        .filesize {{ color: var(--text-secondary); font-size: 0.9rem; }}
        .results-table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        .results-table th, .results-table td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--divider); }}
        .results-table th {{ color: var(--text-secondary); background: var(--bg); }}
        .results-table td {{ font-family: monospace; font-size: 0.9rem; }}
        .no-data {{ text-align: center; color: var(--text-secondary); padding: 2rem; }}
        .about-section {{ max-width: 900px; margin: 0 auto 2rem auto; padding: 1.5rem; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 8px; line-height: 1.6; }}
        .about-section h2 {{ margin-top: 0; color: var(--text-secondary); }}
        .about-section p {{ color: var(--text-secondary); margin: 1rem 0; }}
        .about-section code {{ background: var(--bg); padding: 0.2rem 0.5rem; border-radius: 4px; font-family: monospace; }}
        .about-section pre {{ background: var(--bg); padding: 1rem; border-radius: 6px; overflow-x: auto; font-size: 0.9rem; }}
        .about-section ul {{ color: var(--text-secondary); margin: 1rem 0; padding-left: 1.5rem; }}
        .about-section li {{ margin: 0.5rem 0; }}
    </style>
    <div class="nav">
        <a href="contents">Home</a>
        <a href="memspeed/data">JSON API</a>
    </div>
    <h1>Memory Bandwidth Benchmark</h1>

    <div class="about-section">
        <h2>About</h2>
        <p>
            This tool measures memory bandwidth by writing to buffers of increasing size.
            The resulting curve reveals CPU cache hierarchy: L1 cache (fastest), L2, L3, and main RAM (slowest).
            Sharp drops in speed indicate transitions between cache levels.
        </p>
        <p>
            The chart uses a log-log scale to clearly show performance across buffer sizes from 1KB to 1GB.
            Compare results across different machines to see how CPU architecture and RAM speed affect performance.
        </p>

        <h2>How to Run</h2>
        <p>Download the source or pre-built binary, run the benchmark, and upload your results:</p>
        <pre># Option 1: Download and compile from source
tar -xzf memspeed-src.tar.gz
gcc ms.c -o ms

# Option 2: Use pre-built binary (Linux x86_64)
chmod +x ms-linux-x86_64
./ms-linux-x86_64

# Run benchmark and generate results
./ms > all.out
grep -v Reps all.out > data.csv
./export_json.py > result.json</pre>
        <p>Then upload <code>result.json</code> using the form below, or via curl:</p>
        <pre>curl -u ":PASSWORD" -X POST -H "Content-Type: application/json" \\
  -d @result.json https://cv.petergrecian.co.uk/memspeed/upload</pre>
    </div>

    <div class="chart-container">
        <div class="chart-title">Memory Read Speed vs Buffer Size (Log-Log Scale)</div>
        <canvas id="memspeedChart"></canvas>
    </div>

    {downloads_html}

    {results_table if results else '<p class="no-data">No benchmark results yet. Upload your results below.</p>'}

    <div class="upload-section">
        <h2>Upload Results</h2>
        <form class="upload-form" id="uploadForm">
            <input type="file" id="jsonFile" accept=".json" required>
            <button type="submit" id="uploadBtn">Upload Benchmark</button>
            <div id="uploadStatus"></div>
        </form>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 1rem;">
            Generate JSON with: <code style="background: var(--bg); padding: 0.2rem 0.4rem; border-radius: 3px;">./export_json.py &gt; result.json</code>
        </p>
    </div>

    <script>
    const datasets = {json.dumps(datasets_js)};

    if (datasets.length > 0) {{
        new Chart(document.getElementById('memspeedChart'), {{
            type: 'scatter',
            data: {{ datasets: datasets }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                scales: {{
                    x: {{
                        type: 'logarithmic',
                        title: {{ display: true, text: 'Buffer Size (bytes)', color: '#aaa' }},
                        ticks: {{
                            color: '#888',
                            callback: function(value) {{
                                if (value >= 1e9) return (value/1e9) + ' GB';
                                if (value >= 1e6) return (value/1e6) + ' MB';
                                if (value >= 1e3) return (value/1e3) + ' KB';
                                return value + ' B';
                            }}
                        }},
                        grid: {{ color: '#333' }}
                    }},
                    y: {{
                        type: 'logarithmic',
                        title: {{ display: true, text: 'Speed (bytes/sec)', color: '#aaa' }},
                        ticks: {{
                            color: '#888',
                            callback: function(value) {{
                                if (value >= 1e9) return (value/1e9) + ' GB/s';
                                if (value >= 1e6) return (value/1e6) + ' MB/s';
                                if (value >= 1e3) return (value/1e3) + ' KB/s';
                                return value + ' B/s';
                            }}
                        }},
                        grid: {{ color: '#333' }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        labels: {{ color: '#aaa' }},
                        position: 'top'
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const size = context.parsed.x;
                                const speed = context.parsed.y;
                                let sizeStr = size >= 1e6 ? (size/1e6).toFixed(1) + ' MB' : (size/1e3).toFixed(1) + ' KB';
                                let speedStr = (speed/1e9).toFixed(2) + ' GB/s';
                                return context.dataset.label + ': ' + sizeStr + ' @ ' + speedStr;
                            }}
                        }}
                    }}
                }}
            }}
        }});
    }}

    document.getElementById('uploadForm').addEventListener('submit', async function(e) {{
        e.preventDefault();
        const fileInput = document.getElementById('jsonFile');
        const status = document.getElementById('uploadStatus');
        const btn = document.getElementById('uploadBtn');

        if (!fileInput.files[0]) {{
            status.textContent = 'Please select a file';
            status.style.color = '#ef4444';
            return;
        }}

        btn.disabled = true;
        btn.textContent = 'Uploading...';
        status.textContent = '';

        try {{
            const text = await fileInput.files[0].text();
            const data = JSON.parse(text);

            const response = await fetch('memspeed/upload', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(data)
            }});

            const result = await response.json();

            if (response.ok) {{
                status.textContent = result.message || 'Upload successful!';
                status.style.color = '#10b981';
                setTimeout(() => location.reload(), 1500);
            }} else {{
                status.textContent = result.error || 'Upload failed';
                status.style.color = '#ef4444';
            }}
        }} catch (err) {{
            status.textContent = 'Error: ' + err.message;
            status.style.color = '#ef4444';
        }}

        btn.disabled = false;
        btn.textContent = 'Upload Benchmark';
    }});
    </script>
    '''


MYWEBSITE_CONTENTS_TABLE = "mywebsite-contents"


def get_srfcplus_cookie():
    """Fetch the stored SRFC session cookie from SSM (not cached — user can update it)."""
    return get_parameter(SRFCPLUS_COOKIE_PARAM)


def save_srfcplus_cookie(value):
    """Save the SRFC session cookie to SSM Parameter Store."""
    if not BOTO3_AVAILABLE:
        return False
    try:
        import boto3
        ssm = boto3.client('ssm', region_name=GARDENCAM_REGION)
        ssm.put_parameter(Name=SRFCPLUS_COOKIE_PARAM, Value=value, Type='SecureString', Overwrite=True)
        return True
    except Exception as e:
        print(f"Error saving SRFC cookie: {e}")
        return False


def fetch_srfcplus_homepage(cookie):
    """Fetch and sanitise the real SRFC homepage. Returns (html, error)."""
    import urllib.request, re

    try:
        req = urllib.request.Request(
            'https://www.mysurbitonracketfitness.com/pages/homepage.aspx',
            headers={
                'Cookie': cookie,
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-GB,en;q=0.9',
            }
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            final_url = resp.url
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None, str(e)

    if 'login.aspx' in final_url.lower():
        return None, 'expired'

    # Fix relative URLs: add <base> tag so images/CSS/JS load from the real site
    html = html.replace('<head>', '<head>\n  <base href="https://www.mysurbitonracketfitness.com/pages/">', 1)

    # Remove financial / personal alert tiles — keep only the booking count tile
    # Each tile: <div class="alerttile ...">...<div class="alerttextpanel ...">text</div></a></div>
    STRIP_KEYWORDS = ['invoice', 'virtual wallet', '£', 'profile image',
                      'bar will be closed', 'private function', 'closed from']

    def filter_tile(m):
        tile = m.group(0)
        if any(kw in tile.lower() for kw in STRIP_KEYWORDS):
            return ''
        return tile

    html = re.sub(r'<div class="alerttile[^"]*">.*?</a>\s*</div>', filter_tile, html, flags=re.DOTALL)
    # Also strip plain message tiles (bar notices, announcements — no <a> wrapper)
    html = re.sub(r'<div class="alerttile[^"]*">(?:(?!alerttile).)*alerttilemessage.*?</div>\s*</div>',
                  '', html, flags=re.DOTALL)

    # Inject SRFC Plus top bar
    top_bar = (
        '<div style="background:#1a3070;color:#fff;text-align:center;padding:5px 0;'
        'font-size:11px;font-family:Quicksand,\'Open Sans\',sans-serif;letter-spacing:1px;">'
        'SRFC PLUS &nbsp;|&nbsp; '
        '<a href="/srfcplus/update-cookie" style="color:#87b4e8;">update session</a>'
        ' &nbsp;|&nbsp; '
        '<a href="/contents" style="color:#87b4e8;">petergrecian.co.uk</a>'
        '</div>'
    )
    html = re.sub(r'(<body[^>]*>)', r'\1' + top_bar, html, count=1)

    return html, None


def render_srfcplus_setup_page(message=None, success=False):
    """Render the SRFC Plus cookie setup/update page in SRFC portal style."""
    msg_html = ''
    if message and not success:
        msg_html = f'<div class="alert alert-danger" style="margin-bottom:1rem;">{message}</div>'
    if success:
        msg_html = '<div class="alert alert-success" style="margin-bottom:1rem;">Cookie saved. <a href="/srfcplus">Go to SRFC Plus →</a></div>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SRFC Plus — Setup</title>
  <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: "Quicksand","Open Sans",Verdana,Arial,sans-serif; font-size:13px; background:#f5f7fa; color:#333; margin:0; }}
    .navbar {{ background:#23408f; min-height:60px; display:flex; align-items:center; padding:0 20px; }}
    .navbar img {{ max-height:40px; }}
    .navbar a {{ color:#ddd; margin-left:auto; font-size:12px; font-weight:600; text-decoration:none; }}
    .container {{ max-width:560px; margin:40px auto; padding:0 20px; }}
    .panel {{ background:#fff; border:1px solid #e5e5e5; border-radius:4px; }}
    .panel-heading {{ background:#f5f5f5; border-bottom:1px solid #e5e5e5; padding:10px 16px; font-weight:700; font-size:13px; }}
    .panel-body {{ padding:20px; }}
    label {{ display:block; font-weight:700; font-size:11px; color:#555; margin-bottom:6px; text-transform:uppercase; letter-spacing:.04em; }}
    textarea {{ width:100%; box-sizing:border-box; font-family:monospace; font-size:11px; border:1px solid #ddd; border-radius:3px; padding:8px; resize:vertical; min-height:70px; }}
    .hint {{ font-size:11px; color:#888; margin-top:6px; line-height:1.5; }}
    .hint code {{ background:#f5f5f5; padding:1px 4px; border-radius:2px; font-size:10px; }}
    .btn {{ background:#2ba6cb; color:#fff; border:1px solid #2285a2; padding:8px 20px; border-radius:3px; font-family:inherit; font-size:13px; font-weight:700; cursor:pointer; margin-top:12px; }}
    .btn:hover {{ background:#2285a2; }}
    .alert-danger {{ background:#fdf2f2; border:1px solid #f5c6cb; color:#721c24; padding:10px 14px; border-radius:3px; font-size:12px; }}
    .alert-success {{ background:#f2fdf5; border:1px solid #c3e6cb; color:#155724; padding:10px 14px; border-radius:3px; font-size:12px; }}
    .alert-success a {{ color:#155724; }}
  </style>
</head>
<body>
  <nav class="navbar">
    <img src="https://backoffice.mysurbitonracketfitness.com/imageorganisation/pageheaderlogo/moc_surbiton_live_orgbannerlogo.png" alt="SRFC">
    <a href="/contents">petergrecian.co.uk</a>
  </nav>
  <div class="container">
    <h2 style="color:#23408f;margin-bottom:1.5rem;">SRFC Plus — Session Setup</h2>
    {msg_html}
    <div class="panel">
      <div class="panel-heading">Portal Session Cookie</div>
      <div class="panel-body">
        <form method="POST" action="/srfcplus/update-cookie">
          <label>Cookie string</label>
          <textarea name="cookie" placeholder="ASP.NET_SessionId=abc123; .ASPXAUTH=xyz..."></textarea>
          <p class="hint">
            Log in at <a href="https://www.mysurbitonracketfitness.com" target="_blank">mysurbitonracketfitness.com</a>,
            then open DevTools (F12) → Application → Storage → Cookies →
            <strong>www.mysurbitonracketfitness.com</strong>.<br>
            Copy <code>ASP.NET_SessionId</code> and <code>.ASPXAUTH</code> and paste as:<br>
            <code>ASP.NET_SessionId=abc123; .ASPXAUTH=xyz...</code><br>
            Saved securely in AWS SSM — works from all devices.
          </p>
          <button type="submit" class="btn">Save Cookie</button>
        </form>
      </div>
    </div>
  </div>
</body>
</html>'''


def fetch_srfcplus_bookings(cookie, sport=None):
    """Fetch bookings from ManageOurClub contact statement page.
    Uses /pages/contact/contactstatement.aspx which loads directly with auth
    and contains a DevExpress grid with booking descriptions including court and time."""
    import urllib.request, re
    from datetime import datetime

    if not cookie:
        return {'error': 'No cookie provided'}

    try:
        url = 'https://www.mysurbitonracketfitness.com/pages/contact/contactstatement.aspx'
        req = urllib.request.Request(url, headers={
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            final_url = resp.url
            body = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return {'error': str(e)}

    if 'login.aspx' in final_url.lower():
        return {'error': 'Session expired — please refresh your cookie from the portal'}

    # Extract DevExpress grid rows
    rows = re.findall(r'<tr[^>]*class="[^"]*dxgvDataRow[^"]*"[^>]*>(.*?)</tr>', body, re.DOTALL)
    if not rows:
        return {'bookings': [], 'note': 'No data found — page structure may have changed'}

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    bookings = []

    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        cells = [re.sub(r'<[^>]+>', '', c).strip().replace('&nbsp;', '').strip() for c in cells]
        if len(cells) < 3:
            continue

        row_type = cells[0]
        date_str = cells[1]
        description = cells[2]

        if row_type != 'Booking':
            continue

        # Only future bookings
        try:
            row_date = datetime.strptime(date_str, '%d %b %Y')
            if row_date < today:
                continue
        except ValueError:
            pass

        if sport and sport.lower() not in description.lower():
            continue

        booking = {'date': date_str, 'description': description}

        # "Booking for X on Day D Mon YYYY - Venue - Padel Court N from HH:MM to HH:MM"
        m = re.search(r'on (\w{3} \d+ \w+ \d{4}) - [^-]+ - (Padel[^-]+?) from (\d{2}:\d{2}) to (\d{2}:\d{2})', description)
        if m:
            booking['event_date'] = m.group(1)
            booking['court'] = m.group(2).strip()
            booking['start'] = m.group(3)
            booking['end'] = m.group(4)
        else:
            # "Place booked for X on DayName Event Name on Day Mon at Venue"
            m2 = re.search(r'on (\w{3} \d+ \w+)(?: \d{4})? at ', description)
            if m2:
                booking['event_date'] = m2.group(1)
            # Extract event name
            m3 = re.search(r'(?:Booking|Place booked) for [^-]+ - (.+)', description)
            if not m3:
                m3 = re.search(r'Invoice \d+ - (.+)', description)
            booking['label'] = m3.group(1).strip() if m3 else description

        bookings.append(booking)

    return {'bookings': bookings, 'count': len(bookings), 'sport': sport}


def render_srfcplus_page():
    """Render the SRFC Plus companion page, styled to match the real ManageOurClub portal."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Bookings — Surbiton Racket &amp; Fitness Club</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&family=Open+Sans:wght@400;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: "Quicksand", "Open Sans", Verdana, Arial, sans-serif; font-size: 13px; background: #f5f7fa; color: #333; min-height: 100vh; }

    /* ── Navbar ── */
    .navbar { background: #23408f; min-height: 60px; display: flex; align-items: center; padding: 0 20px; border-bottom: 1px solid #1a3070; }
    .navbar-logo { display: flex; align-items: center; }
    .navbar-logo img { max-height: 40px; }
    .navbar-right { margin-left: auto; display: flex; align-items: center; gap: 16px; }
    .navbar-right a { color: #ddd; text-decoration: none; font-size: 12px; font-weight: 600; }
    .navbar-right a:hover { color: #fff; }
    .navbar-right .btn-signout { background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: #fff; padding: 5px 12px; border-radius: 3px; cursor: pointer; font-family: inherit; font-size: 12px; font-weight: 600; }
    .navbar-right .btn-signout:hover { background: rgba(255,255,255,0.25); }

    /* ── Sub-nav tabs ── */
    .subnav { background: #fff; border-bottom: 1px solid #ddd; padding: 0 20px; display: flex; gap: 0; }
    .subnav a { display: inline-block; padding: 12px 16px; font-size: 12px; font-weight: 600; color: #555; text-decoration: none; border-bottom: 3px solid transparent; }
    .subnav a:hover { color: #23408f; border-bottom-color: #619fe0; }
    .subnav a.active { color: #23408f; border-bottom-color: #23408f; }

    /* ── Page container ── */
    .container { max-width: 960px; margin: 24px auto; padding: 0 20px; }

    /* ── Page title ── */
    .page-title { font-size: 22px; font-weight: 700; color: #23408f; margin-bottom: 4px; }
    .page-subtitle { color: #888; font-size: 12px; margin-bottom: 20px; }

    /* ── Bookings table ── */
    .panel { background: #fff; border: 1px solid #e5e5e5; border-radius: 4px; margin-bottom: 20px; }
    .panel-heading { background: #f5f5f5; border-bottom: 1px solid #e5e5e5; padding: 10px 16px; font-weight: 700; font-size: 13px; color: #333; border-radius: 4px 4px 0 0; display: flex; justify-content: space-between; align-items: center; }
    .panel-body { padding: 0; }
    table.bookings { width: 100%; border-collapse: collapse; font-size: 12px; }
    table.bookings th { background: #f9f9f9; color: #555; font-weight: 700; text-align: left; padding: 9px 14px; border-bottom: 1px solid #e5e5e5; white-space: nowrap; }
    table.bookings td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
    table.bookings tr:last-child td { border-bottom: none; }
    table.bookings tr:hover td { background: #fafbff; }
    .badge-confirmed { display: inline-block; background: #65b589; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .badge-pending { display: inline-block; background: #f0ad4e; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 700; text-transform: uppercase; }

    /* ── Status messages ── */
    .status-msg { padding: 20px; text-align: center; color: #888; font-size: 13px; }
    .status-msg.error { color: #c60f13; }
    .loading-spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #ddd; border-top-color: #23408f; border-radius: 50%; animation: spin 0.7s linear infinite; vertical-align: middle; margin-right: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Cookie config panel ── */
    .config-toggle { font-size: 11px; color: #2ba6cb; cursor: pointer; text-decoration: underline; background: none; border: none; font-family: inherit; padding: 0; }
    .config-panel { display: none; padding: 14px 16px; background: #fffef0; border-top: 1px solid #e5e5e5; }
    .config-panel.open { display: block; }
    .config-panel label { display: block; font-weight: 700; font-size: 11px; color: #555; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.04em; }
    .config-panel textarea { width: 100%; font-family: monospace; font-size: 11px; border: 1px solid #ddd; border-radius: 3px; padding: 7px; resize: vertical; min-height: 60px; color: #333; }
    .config-panel .hint { font-size: 11px; color: #888; margin-top: 5px; line-height: 1.5; }
    .config-panel .btn-row { display: flex; gap: 8px; margin-top: 10px; }
    .btn-primary { background: #2ba6cb; color: #fff; border: 1px solid #2285a2; padding: 7px 16px; border-radius: 3px; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
    .btn-primary:hover { background: #2285a2; }
    .btn-secondary { background: #e9e9e9; color: #333; border: 1px solid #bababa; padding: 7px 16px; border-radius: 3px; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
    .btn-secondary:hover { background: #bababa; }

    /* ── Footer ── */
    .footer { text-align: center; padding: 20px; color: #aaa; font-size: 11px; border-top: 1px solid #e5e5e5; margin-top: 20px; }
    .footer a { color: #2ba6cb; text-decoration: none; }

    @media (max-width: 600px) {
      .subnav { overflow-x: auto; }
      table.bookings th, table.bookings td { padding: 8px 10px; }
      .container { padding: 0 10px; }
    }
  </style>
</head>
<body>

  <!-- Navbar -->
  <nav class="navbar">
    <div class="navbar-logo">
      <img src="https://backoffice.mysurbitonracketfitness.com/imageorganisation/pageheaderlogo/moc_surbiton_live_orgbannerlogo.png" alt="Surbiton Racket &amp; Fitness Club">
    </div>
    <div class="navbar-right">
      <a href="https://www.mysurbitonracketfitness.com/pages/homepage.aspx" target="_blank">Full Portal ↗</a>
      <a href="/contents">petergrecian.co.uk</a>
    </div>
  </nav>

  <!-- Sub-nav -->
  <div class="subnav">
    <a href="#" class="active">My Bookings</a>
    <a href="https://www.mysurbitonracketfitness.com/pages/user/detailsummary.aspx" target="_blank">My Details</a>
    <a href="https://www.mysurbitonracketfitness.com/pages/checkout/cartdetails.aspx" target="_blank">Shopping Cart</a>
  </div>

  <div class="container">
    <div class="page-title">My Padel Bookings</div>
    <div class="page-subtitle">Padel court reservations — loaded directly from the portal</div>

    <div class="panel">
      <div class="panel-heading">
        <span>Bookings</span>
        <button class="config-toggle" onclick="toggleConfig()">⚙ Cookie settings</button>
      </div>

      <!-- Cookie config (hidden by default) -->
      <div class="config-panel" id="configPanel">
        <label>ASP.NET_SessionId cookie</label>
        <textarea id="cookieInput" placeholder="Paste your full cookie string here&#10;e.g. ASP.NET_SessionId=abc123xyz..."></textarea>
        <p class="hint">Log into <a href="https://www.mysurbitonracketfitness.com" target="_blank">mysurbitonracketfitness.com</a>, then open DevTools (F12) → Application → Storage → Cookies → <strong>www.mysurbitonracketfitness.com</strong>. Copy the <strong>ASP.NET_SessionId</strong> value (and <strong>.ASPXAUTH</strong> if present) and paste in the format:<br><code>ASP.NET_SessionId=abc123; .ASPXAUTH=xyz...</code><br>Stored only in your browser, never sent to this server except to proxy the request.</p>
        <div class="btn-row">
          <button class="btn-primary" onclick="saveCookie()">Save &amp; Reload</button>
          <button class="btn-secondary" onclick="clearCookie()">Clear</button>
        </div>
      </div>

      <div class="panel-body">
        <div class="status-msg" id="statusMsg">
          <span class="loading-spinner"></span> Loading bookings…
        </div>
        <table class="bookings" id="bookingsTable" style="display:none">
          <thead id="bookingsHead"></thead>
          <tbody id="bookingsBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="footer">
    SRFC Plus — faster view of <a href="https://www.mysurbitonracketfitness.com" target="_blank">mysurbitonracketfitness.com</a>
  </div>

  <script>
    const COOKIE_KEY = 'srfcplus_cookie';
    const escHtml = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

    function toggleConfig() {
      const p = document.getElementById('configPanel');
      p.classList.toggle('open');
      if (p.classList.contains('open')) {
        const saved = localStorage.getItem(COOKIE_KEY);
        if (saved) document.getElementById('cookieInput').value = saved;
      }
    }

    function saveCookie() {
      const val = document.getElementById('cookieInput').value.trim();
      if (!val) { alert('Please paste your cookie first.'); return; }
      localStorage.setItem(COOKIE_KEY, val);
      document.getElementById('configPanel').classList.remove('open');
      loadBookings(val);
    }

    function clearCookie() {
      localStorage.removeItem(COOKIE_KEY);
      document.getElementById('cookieInput').value = '';
      showStatus('Cookie cleared. Paste a new cookie to load bookings.');
    }

    function showStatus(msg, isError) {
      const el = document.getElementById('statusMsg');
      el.innerHTML = msg;
      el.className = 'status-msg' + (isError ? ' error' : '');
      el.style.display = '';
      document.getElementById('bookingsTable').style.display = 'none';
    }

    function loadBookings(cookie) {
      showStatus('<span class="loading-spinner"></span> Loading bookings…');

      fetch('/srfcplus/bookings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({cookie: cookie})
      })
        .then(r => r.json())
        .then(data => {
          if (data.error) { showStatus('⚠ ' + escHtml(data.error), true); return; }

          const bookings = data.bookings || [];
          if (!bookings.length) {
            showStatus(escHtml(data.note || 'No upcoming bookings found.'));
            return;
          }

          const thead = document.getElementById('bookingsHead');
          const tbody = document.getElementById('bookingsBody');
          thead.innerHTML = '<tr><th>Court / Event</th><th>Date</th><th>Time</th></tr>';
          tbody.innerHTML = '';

          bookings.forEach(b => {
            const tr = document.createElement('tr');
            const title = b.court || b.label || b.description || '';
            const when  = b.event_date || b.date || '';
            const time  = (b.start && b.end) ? b.start + '\u2013' + b.end : '';
            tr.innerHTML =
              '<td><strong>' + escHtml(title) + '</strong></td>' +
              '<td>' + escHtml(when) + '</td>' +
              '<td>' + escHtml(time) + '</td>';
            tbody.appendChild(tr);
          });

          document.getElementById('statusMsg').style.display = 'none';
          document.getElementById('bookingsTable').style.display = '';
        })
        .catch(e => showStatus('⚠ Request failed: ' + escHtml(e.message), true));
    }

    window.addEventListener('DOMContentLoaded', () => {
      const saved = localStorage.getItem(COOKIE_KEY);
      if (saved) {
        loadBookings(saved);
      } else {
        showStatus('No cookie saved yet — click <strong>⚙ Cookie settings</strong> above to get started.');
        document.getElementById('configPanel').classList.add('open');
      }
    });
  </script>
</body>
</html>'''


def render_contents_page():
    """Render the contents/navigation page from DynamoDB mywebsite-contents table."""
    items = []
    if BOTO3_AVAILABLE:
        try:
            dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
            table = dynamodb.Table(MYWEBSITE_CONTENTS_TABLE)
            response = table.scan()
            items = response.get('Items', [])
        except Exception as e:
            print(f"Error reading {MYWEBSITE_CONTENTS_TABLE}: {e}")

    # Sort by sort_order
    items.sort(key=lambda x: int(x.get('sort_order', 999)))

    # Filter to visible items only
    items = [i for i in items if i.get('visible', True)]

    # Build links HTML
    links_html = ""
    for item in items:
        path = item.get('path', '/')
        href = item.get('external_url', path)
        title = item.get('title', '')
        description = item.get('description', '')
        private_badge = '<sup style="font-size:0.55em; vertical-align:super; color:var(--text-secondary); font-weight:400; letter-spacing:0.05em;">PRIVATE</sup>' if item.get('auth_required') else ''
        links_html += f'''      <a href="{href}" class="link-ellipse">
        {title}{private_badge}
        <span class="description">{description}</span>
      </a>\n'''

    return f'''<html lang="en">
  <head>
    <title>Peter Grecian</title>
    <style>
      body {{ font-family: var(--font); text-align: center; background: var(--bg); min-height: 100vh; margin: 0; padding: 2rem; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text); }}
      h1 {{ color: var(--text); font-size: 2.5rem; margin-bottom: 2rem; }}
      .links-container {{ display: flex; flex-direction: column; gap: 0.75rem; width: 100%; max-width: 500px; }}
      .link-ellipse {{ display: block; padding: 0.9rem 2rem; border-radius: 50px; text-decoration: none; font-size: 1.1rem; font-weight: 500; color: var(--accent); background: var(--card-bg); border: 1px solid var(--divider); transition: opacity 0.2s; }}
      .link-ellipse:hover {{ opacity: 0.8; }}
      .link-ellipse .description {{ display: block; font-size: 0.8rem; margin-top: 0.2rem; color: var(--text-secondary); font-weight: normal; }}
      .hero-img {{ width: 100%; max-width: 500px; border-radius: 12px; margin-bottom: 1.5rem; object-fit: cover; max-height: 200px; }}
      @media (max-width: 768px) {{ h1 {{ font-size: 2rem; margin-bottom: 1.5rem; }} .link-ellipse {{ padding: 0.8rem 1.5rem; font-size: 1rem; }} }}
    </style>
    {THEME_CSS_JS}
  </head>
  <body>
    <img class="hero-img" src="https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260113_100124014.jpg" alt="Waterloo station">
    <h1>Peter Grecian</h1>
    <div class="links-container">
{links_html}    </div>
  </body>
</html>'''


def render_gotg_page():
    """Render Götterdämmerung on the Go — scene-by-scene listening guide with liner notes."""
    scenes = [
        {
            'num': 1, 'title': 'The Norns', 'act': 'Prologue',
            'tracks': '1–4', 'duration': '19:19',
            'location': "Brünnhilde's rock, night",
            'characters': 'Three Norns (Daughters of Erda)',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/b/b2/Siegfried_and_the_Twilight_of_the_Gods_p_104.jpg',
            'img_credit': 'Arthur Rackham, 1911',
            'synopsis': 'Three fate-weaving Norns recount the history of gods and the Ring while passing a golden rope between them. The First Norn recalls Wotan breaking a branch from the World Ash Tree to make his spear of law. The Second tells how Siegfried shattered that spear. The Third sees Valhalla surrounded by piled wood, awaiting fire. The rope tangles, the weaving grows desperate — and the rope <strong>breaks</strong>. Fate itself has ended. In terror, they vanish to their mother Erda. Dawn breaks.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260317_180040500.jpg',
            'atmos_alt': 'London skyline at dusk — twilight of the gods',
            'atmos_credit': 'Peter Grecian',
            'performers': '<img class="perf-photo" src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/Birgitta_Svend%C3%A9n_2013.jpg/150px-Birgitta_Svend%C3%A9n_2013.jpg" alt="Birgitta Svendén"><strong>Birgitta Svenden</strong> (First Norn) — Swedish mezzo, Bayreuth regular 1983-99, later General Manager of the Royal Swedish Opera. <strong>Linda Finnie</strong> (Second Norn / also Waltraute in Scene 5) — Scottish contralto, one of the recording\'s standout voices. <strong>Uta Priew</strong> (Third Norn) — German mezzo, long collaboration with director Harry Kupfer who staged this production.',
            'context': 'Wagner wrote this scene <em>last</em> (1874), even though it comes first — a Greek-chorus prologue framing the human drama within cosmic twilight. The three women deliberately echo Shakespeare\'s Weird Sisters in <em>Macbeth</em>, but with a crucial difference: Shakespeare\'s witches tempt the hero toward doom through ambiguous prophecy; Wagner\'s Norns are helpless witnesses whose power breaks, making way for genuine human choice.',
            'quote': '<em>"Es riss! Es riss!"</em> — It broke! It broke!',
            'musical': 'Low strings create primordial darkness. Chromatic harmonies dissolve as the Norns weave faster. Listen for fragmenting Valhalla and World Ash motifs colliding as order breaks down. Three female voices pass phrases like the rope — overlapping entries, shared melodic material, increasing agitation.',
            'tip': 'Focus on atmosphere and the rope breaking (Track 4, final minutes). The rope breaking is the opera\'s thesis statement: determinism has ended, human choice becomes possible.',
            'playlist': 'PLeMsytZrLIuY-6MBFLlOFGhKEm-Ft6pvF',
        },
        {
            'num': 2, 'title': 'Farewell & Rhine Journey', 'act': 'Prologue',
            'tracks': '5–10', 'duration': '21:14',
            'location': "Brünnhilde's rock, then the Rhine",
            'characters': 'Brünnhilde, Siegfried',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/9/9b/Ring52.jpg',
            'img_credit': 'Arthur Rackham, 1911',
            'synopsis': 'Dawn breaks. Siegfried and Brünnhilde emerge from their night together for an ecstatic farewell. She urges him to new deeds; he gives her the Ring as a love-token. She gives him her horse Grane and her wisdom. He rejects wisdom: <em>"my own valor is enough"</em> — this is his tragic flaw, not arrogance but innocence. They part in joy. Neither suspects what\'s coming. The orchestral Rhine Journey (Track 10) depicts Siegfried\'s descent from the mythic heights into the corrupt world below.',
            'performers': '<strong>Anne Evans</strong> (Brünnhilde) — British soprano, DBE, combined vocal power with profound dramatic intelligence. Bayreuth 1989-92. Her Immolation Scene (Scene 12) is the recording\'s crown. <strong>Siegfried Jerusalem</strong> (Siegfried) — German Heldentenor, originally a bassoonist. One of the last great heroic tenors who combined Wagnerian power with lyrical beauty.',
            'context': 'This is the last time Brünnhilde and Siegfried are happy and together. Everything that follows is betrayal, confusion, and catastrophe. Siegfried giving the Ring seems loving, but it removes the curse-bearer from the hero who might break it and places it within the Gibichungs\' reach.',
            'quote': '<em>"Zu neuen Taten, teurer Helde"</em> — To new deeds, dear hero',
            'musical': 'Track 10 (Siegfried\'s Rhine Journey) is one of Wagner\'s greatest orchestral passages — a tone poem shifting from heroic C-major horn calls through nature motifs to darker harmonies. It works as a standalone concert piece. The transition from bright major to ominous minor mirrors the journey from myth to modernity.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260317_134623360.jpg',
            'atmos_alt': 'London panorama through office window — the journey begins',
            'atmos_credit': 'Peter Grecian',
            'tip': 'This is the last moment of happiness. Follow the horn calls in Track 10 as they darken — Siegfried approaches the Gibichung hall and his doom.',
            'playlist': 'PLeMsytZrLIubnRWkKqmcWRJsm6cgMj-su',
        },
        {
            'num': 3, 'title': "Hagen's Plot", 'act': 'Act 1',
            'tracks': '11–20', 'duration': '32:42',
            'location': 'Gibichung Hall by the Rhine',
            'characters': 'Hagen, Gunther, Gutrune, Siegfried',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/e/e7/Siegfried_and_the_Twilight_of_the_Gods_p_120.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; Siegfried hands the drinking-horn back to Gutrune',
            'synopsis': 'The scene shifts from mythic heights to mundane ambition. Hagen manipulates his half-siblings: Gunther (weak king wanting reputation) needs a wife, Gutrune needs a husband. His solution: a potion to make Siegfried forget Brünnhilde, marry Gutrune, then use the Tarnhelm to fetch Brünnhilde for Gunther. Siegfried arrives, drinks the welcome cup — memory erased. He instantly forgets his love and becomes infatuated with Gutrune. They swear blood-brotherhood (<em>Blutbruderschaft</em>) and depart to abduct Brünnhilde. Wagner\'s irony: the Ring\'s freest hero, reduced to puppet through chemistry.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260109_101519827.jpg',
            'atmos_alt': 'Guildhall — a medieval great hall in the City',
            'atmos_credit': 'Peter Grecian',
            'performers': '<img class="perf-photo" src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Eva-Maria_Bundschuh_1987.jpg/150px-Eva-Maria_Bundschuh_1987.jpg" alt="Eva-Maria Bundschuh, 1987"><strong>Philip Kang</strong> (Hagen) — Korean-German bass, the <em>first Asian singer to perform major Wagnerian roles at Bayreuth</em> (1988-92). His Hagen embodied pure malevolence with unsettling stillness. <strong>Bodo Brinkmann</strong> (Gunther) — German baritone, portrayed Gunther as nobility without strength. <strong>Eva-Maria Bundschuh</strong> (Gutrune, pictured 1987) — German soprano, innocence destroyed by proximity to power.',
            'context': 'The Gibichungs represent modernity\'s mediocrity — bureaucrats and social climbers inheriting a heroic age they can\'t comprehend. They use technology (potion, Tarnhelm) rather than authentic strength. Wagner saw them as the German bourgeoisie after 1848. Siegfried isn\'t cursed or fated — he\'s <em>drugged</em>. This makes the tragedy more disturbing than divine manipulation.',
            'quote': '<em>"Willkommen, Gast, in Gibichs Haus!"</em> — Welcome, guest, to Gibich\'s house!',
            'musical': 'Listen for the orchestral transformation at Track 17: Siegfried toasts "Brünnhilde!" — drinks — the love theme inverts into hollow emptiness — a new false-love theme for Gutrune emerges. Psychological destruction through leitmotif manipulation.',
            'tip': 'The potion scene (Track 17) is devastating. The blood oath (Track 19) is a dark parody of heroic music — solemn ritual for a manipulated alliance.',
            'playlist': 'PLeMsytZrLIubQfPCF2hUF3BrGxw4gCnlZ',
        },
        {
            'num': 4, 'title': "Hagen's Watch", 'act': 'Act 1',
            'tracks': '21', 'duration': '11:08',
            'location': 'Gibichung Hall, night',
            'characters': 'Hagen (alone)',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/d/d4/Siegfried_and_the_Twilight_of_the_Gods_p_128.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; The ravens of Wotan',
            'synopsis': 'Everyone has departed. Hagen sits alone in darkness — 11 minutes of pure malevolence. He reveals his true thoughts: he manipulates Gunther and Gutrune like puppets; he\'ll get the Ring for his father Alberich; once he has it, the Nibelungs will rule the world. He never sleeps. The scene ends with him motionless, watching.',
            'performers': '<strong>Philip Kang</strong> — His Watch scene remains one of the most chilling performances of Wagner\'s patient villain. Lean, focused, modern psychology rather than cartoonish evil.',
            'context': 'Like Iago in <em>Othello</em> or Richard III, Hagen reveals himself to the audience alone. But Iago improvises brilliantly; Hagen plans methodically. Iago is Renaissance villainy (wit, improvisation). Hagen is industrial-era villainy (system, patience, instrumentalism). Wagner, influenced by Schopenhauer, saw Hagen as pure will-to-power without being — all striving, no rest. He never sleeps: the nightmare of modernity, perpetual vigilance.',
            'quote': '<em>"Hier sitz\' ich zur Wacht, wahre den Hof"</em> — Here I sit on watch, guard the court<br><small>(Irony: the real threat comes from inside — from Hagen himself.)</small>',
            'musical': 'Built over an obsessive ground bass — repeating, immobile, representing Hagen\'s fixed will and the curse\'s inexorable working. Dark low brass, no upper-register warmth. Wagner wrote this for a true <em>basso profondo</em>, rare even in his time.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260206_133202622.MP.jpg',
            'atmos_alt': 'City in rain — watching over London',
            'atmos_credit': 'Peter Grecian',
            'tip': 'True power doesn\'t need to move. It waits. The stillness is the menace. Compare with Wotan\'s monologues — where Wotan despairs, Hagen calculates.',
            'playlist': 'PLeMsytZrLIuYrGX5nB_kYbjJjYnjM1LKn',
        },
        {
            'num': 5, 'title': "Waltraute's Plea", 'act': 'Act 1',
            'tracks': '22–24', 'duration': '26:36',
            'location': "Brünnhilde's rock",
            'characters': 'Brünnhilde, Waltraute',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/0/08/Siegfried_and_the_Twilight_of_the_Gods_p_130.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; The Ring upon thy hand',
            'synopsis': 'Brünnhilde hears approaching sounds — Siegfried returning? No: her Valkyrie sister Waltraute, with devastating news. In the opera\'s most important narrative passage (Track 23, 12 minutes), Waltraute describes Wotan\'s current state: broken, silent, sitting in Valhalla holding pieces of his shattered spear, dead World Ash wood piled around the hall awaiting fire. Once, Wotan muttered: <em>"If Brünnhilde returned the Ring to the Rhine, gods and world would be redeemed."</em> Waltraute begs. Brünnhilde refuses — the Ring is Siegfried\'s love-token, more precious than Valhalla, more precious than the gods.',
            'performers': '<strong>Linda Finnie</strong> (Waltraute / also Second Norn) — Her Waltraute scene is one of the recording\'s most powerful moments, sustaining both narrative power and emotional depth across nearly half an hour of continuous performance.',
            'context': 'Wotan doesn\'t appear in Gotterdammerung (he dominated the previous operas). His absence is the point — he\'s given up. Cosmic depression: the god of will has lost his will. Brünnhilde must choose: save the gods (return the Ring, obey Wotan\'s indirect command) or keep Siegfried\'s love. She chooses love — humanity over divinity. The dramatic irony is crushing: the Ring she defends as symbol of his love... Siegfried doesn\'t even remember her.',
            'quote': '<em>"Den Ring geb\' ich nicht — eher vergeh\' die Welt!"</em> — I\'ll not give up the Ring — let the world perish first!',
            'musical': 'Waltraute\'s 12-minute narrative uses recitative-like flexibility with orchestral leitmotif commentary — Valhalla majestic but now tragic, the World Ash dying, Wotan\'s spear shattered. Words tell story; orchestra tells meaning.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260220_165308688.jpg',
            'atmos_alt': 'St Paul\'s under grey skies — the gods\' broken world',
            'atmos_credit': 'Peter Grecian',
            'tip': 'Track 23 is a mini-opera within the opera. This is Wagner\'s most powerful messenger scene — 26 minutes of continuous dramatic narrative.',
            'playlist': 'PLeMsytZrLIuYPuDwIpTVy4cKDNL-iKKB4',
        },
        {
            'num': 6, 'title': 'The Abduction', 'act': 'Act 1',
            'tracks': '25–26', 'duration': '12:51',
            'location': "Brünnhilde's rock",
            'characters': 'Brünnhilde, Siegfried (disguised as Gunther)',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/5/52/Siegfried_and_the_Twilight_of_the_Gods_p_124.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; Brünnhilde kisses the Ring',
            'synopsis': 'Storm clouds. Lightning. A figure approaches through the fire — Brünnhilde joyfully assumes Siegfried returns. But the figure emerges as a stranger claiming to be Gunther. (Actually: Siegfried wearing the Tarnhelm.) She holds up the Ring — its magic should protect her. It doesn\'t. He overpowers her, rips the Ring from her finger, drags her into the cave. He places his sword Nothung between them — technically keeping faith with Gunther, but Brünnhilde won\'t know this. She is broken.',
            'performers': '',
            'context': 'From Brünnhilde\'s perspective: a stranger has violated her sanctuary, stolen Siegfried\'s Ring, overpowered her by force. From Siegfried\'s: he\'s helping his blood-brother, keeping his oath, even preserving "honour" with the sword. The potion has made him amnesiac, not evil. But the effect is evil regardless. The man she loves is the man who betrays her — and neither knows they\'re the same person.',
            'quote': '<em>"Brünnhild\'! Ein Freier kam"</em> — Brünnhilde! A suitor came',
            'musical': 'Storm music in Track 25: lightning (brass stabs), thunder (timpani rolls), wind (swirling strings). In Track 26, listen for Siegfried\'s hero motifs underneath "Gunther\'s" voice — the orchestra tells us who he really is, even as she can\'t recognise him.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260106_120336771.jpg',
            'atmos_alt': 'Barbican in snow — storm and violation',
            'atmos_credit': 'Peter Grecian',
            'tip': 'The dramatic irony is devastating. The sword between them echoes the Volsung saga. Act 1 curtain falls on her devastation.',
            'playlist': 'PLeMsytZrLIuZFMCKLSvNuzF7kzPedqdyk',
        },
        {
            'num': 7, 'title': 'Night Conspiracy', 'act': 'Act 2',
            'tracks': '27–29', 'duration': '12:42',
            'location': 'Gibichung hall, night',
            'characters': 'Hagen, Alberich',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/a/a5/Alberich_hagen.jpg',
            'img_credit': 'Arthur Rackham, 1912 &mdash; Swear to me, Hagen, my son!',
            'synopsis': 'Darkness. Hagen sits motionless (does he ever sleep?). His father Alberich — the Nibelung dwarf who forged the Ring and cursed it — appears in a nightmare-vision. Wagner leaves it ambiguous: dream or reality? Father and son share their hatred of the gods. Alberich\'s urgency: Wotan is broken, but Siegfried has the Ring and is dangerously fearless. <em>"Swear it!"</em> Hagen swears to get the Ring. Alberich vanishes. Dawn approaches.',
            'performers': '<strong>Gunter von Kannen</strong> (Alberich) — German bass-baritone (1940-2016). Received his breakthrough from Barenboim in the 1982 Harry Kupfer Ring and continued to portray the cycle\'s original villain throughout his career.',
            'context': 'Two generations of Ring-curse: Alberich renounced love for power and forged the Ring; Hagen inherits lovelessness and pursues it for father. Neither chose this path — they were shaped by the curse itself. Wagner\'s question: can you be responsible for evil you inherited? Hagen\'s tragedy (if he has one): he never had a chance.',
            'quote': '<em>"Schlafst du, Hagen, mein Sohn?"</em> — Are you sleeping, Hagen, my son?',
            'musical': 'Oppressive orchestral darkness. Alberich\'s motifs from Das Rheingold return — the curse made flesh, passed from father to son. The Ring curse dominates the scene.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260310_162109975.MP.jpg',
            'atmos_alt': 'Dramatic clouds over London — darkness gathering',
            'atmos_credit': 'Peter Grecian',
            'tip': 'This brief scene connects Gotterdammerung back to Das Rheingold where it all began. Listen for the Rheingold harmonies.',
            'playlist': 'PLeMsytZrLIubn_iS0OkdhLllw8JsFusao',
        },
        {
            'num': 8, 'title': 'Vassals & Confrontation', 'act': 'Act 2',
            'tracks': '30–40', 'duration': '44:17',
            'location': 'Gibichung hall, public gathering',
            'characters': 'Siegfried, Hagen, Gutrune, Gunther, Brünnhilde, Vassals',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/c/cc/Wagner_-_G%C3%B6tterd%C3%A4mmerung_-_Setting_of_act_II_at_Bayreuth_-_The_Victrola_book_of_the_opera.jpg',
            'img_credit': 'Act II at Bayreuth, from The Victrola Book of the Opera',
            'synopsis': 'Siegfried returns triumphant. Hagen summons vassals with his war horn. When Gunther arrives with veiled, broken Brünnhilde, she sees the Ring on Siegfried\'s finger — the one torn from her last night. Her head snaps up: <em>"Siegfried?! Here?!"</em> She nearly faints. Public accusation erupts. Both swear oaths on Hagen\'s spear: he swears he never wronged her (the potion erased his memory — technically true), she swears he\'s lying (she experienced the abduction — also technically true). Both pour everything into contradictory truths. The contradiction destroys Brünnhilde. Siegfried dismisses her — <em>"her grief disturbs her mind"</em> — and leads Gutrune away to celebrate, cheerful and oblivious.',
            'performers': '',
            'context': 'Hagen\'s perfect crime: he never lies or even speaks much. He gave Siegfried the potion (chemical truth-alteration), suggested the abduction (exploiting amnesia), offered his spear for the oath (neutral arbiter), and watches the truth destroy them (passive observation). The crime is structural — he arranged conditions where truth conflicts with truth. Hagen\'s spear echoes Wotan\'s (divine law), but inverted: justice without mercy, pure retribution. This spear will kill Siegfried in Act 3.',
            'quote': '<em>"Helle Wehr! Heilige Waffe! Hilf meinem ewigen Eide!"</em> — Shining weapon! Holy steel! Witness my eternal oath!',
            'musical': 'The vassals\' chorus is Wagner\'s biggest choral writing in the Ring. The oath-swearing is electrifying — Siegfried\'s confident heroic brass against Brünnhilde\'s jagged desperate leaps, the orchestra undermining both with Ring and Curse motifs. She calls on the gods for witness — they are silent.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260113_100124014.jpg',
            'atmos_alt': 'Waterloo station — the crowd gathers',
            'atmos_credit': 'Peter Grecian',
            'tip': 'The oath duel (Tracks 38-40) is the opera\'s dramatic peak before the murder. Notice what Siegfried <em>doesn\'t hear</em>: the orchestra plays Brünnhilde\'s love theme when she speaks, but he remains unmoved.',
            'playlist': 'PLeMsytZrLIubLA1zF0CDOvFQDzfgfjCsR',
        },
        {
            'num': 9, 'title': 'The Murder Plot', 'act': 'Act 2',
            'tracks': '41–45', 'duration': '17:40',
            'location': 'Gibichung hall',
            'characters': 'Brünnhilde, Hagen, Gunther',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/e/ed/Siegfried_and_the_Twilight_of_the_Gods_p_154.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; O wife betrayed, I will avenge thy trust deceived',
            'synopsis': 'Three conspirators remain, each with different reasons. Brünnhilde, destroyed by betrayal, reveals Siegfried\'s one vulnerability: his back — she never shielded it with magic, assuming he\'d never retreat. <em>"And my spear shall find that spot,"</em> says Hagen coldly. Gunther wavers — <em>"He\'s my blood-brother"</em> — but his honour is already shattered. Hagen barely needs to manipulate: he asks questions, states facts, offers solutions. The murder will be disguised as a hunting accident. Act 2 ends in conspiracy — three figures backlit, the Ring curse grinding in the orchestra.',
            'performers': '',
            'context': 'Brünnhilde betrays Siegfried exactly as she believes he betrayed her. She gave him invincibility out of love; she now tells his enemies how to kill him out of rage. Wagner shows that rage is love inverted — same intensity, opposite direction. She doesn\'t realise she\'s serving Hagen\'s deeper plan. Gunther is pitiable, not villainous — a weak man dragged into murder, whose every line shows hesitation.',
            'quote': '<em>"Seinen Rucken doch traf ihn kein Feind — er bot keinem je ihn dar"</em> — His back no enemy ever struck — he never turned it to a foe',
            'musical': 'Brünnhilde\'s music twists from love themes into vengeance. A new revenge motif emerges — aggressive, march-like. Hagen\'s Watch theme stays underneath, guiding without dominating. Notice how Gunther\'s vocal line keeps reaching up (hoping for a way out) while Hagen\'s stays low and level (inexorable).',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260128_163302319.MP.jpg',
            'atmos_alt': 'Industrial ceiling — cold machinery of conspiracy',
            'atmos_credit': 'Peter Grecian',
            'tip': 'Three motivations, one murder: Brünnhilde wants emotional vengeance, Gunther wants social restoration, Hagen wants the Ring. Only Hagen will achieve his goal.',
            'playlist': 'PLeMsytZrLIuawa4erw8Uz4XAeln97N1Oz',
        },
        {
            'num': 10, 'title': "Rhine Maidens' Warning", 'act': 'Act 3',
            'tracks': '46–52', 'duration': '20:01',
            'location': 'The Rhine, forest',
            'characters': 'Woglinde, Wellgunde, Flosshilde, Siegfried',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/4/46/Siegfried_rhinemaidens.jpg',
            'img_credit': 'Arthur Rackham, 1912 &mdash; Rhine Maidens warn Siegfried',
            'synopsis': 'Dawn on the Rhine. The three Rhine Maidens swim and sing, mourning their lost gold. Siegfried, separated from the hunting party, stumbles upon them. They flirt playfully, asking for the Ring. He almost gives it for fun — then pauses. They turn serious: <em>"Keep it, hero — if you only knew what curse it holds. Give it back to us — we alone can free it."</em> He laughs and refuses. They swim away prophesying his death: <em>"By evening, a woman will inherit the Ring — she\'ll listen to us better."</em> He blows his horn and rejoins the hunt.',
            'performers': '<strong>Hilde Leidland</strong> (Woglinde) — Norwegian soprano (1958-2007). <strong>Annette Kuttenbaum</strong> (Wellgunde) — German mezzo. <strong>Jane Turner</strong> (Flosshilde) — British contralto.',
            'context': 'This scene mirrors Das Rheingold Scene 1 — the cycle\'s opening: same gold, same maidens, same request. But now corrupted. Siegfried\'s refusal makes perfect sense: he\'s never known fear, never experienced loss, never needed consequences. His absolute fearlessness is beautiful but fatal. Wisdom requires acknowledging forces greater than oneself. This is his last chance to escape the curse.',
            'quote': '<em>"Kommt, Schwestern! Schwindet dem Toren!"</em> — Come, sisters! Away from the fool!',
            'musical': 'The Rhine motif returns in its original, uncorrupted form — first heard in Das Rheingold, fragmented throughout the cycle, here briefly restored. Playful water music in thirds darkens into prophecy. Siegfried\'s horn call remains bright and defiant.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260225_102739209.jpg',
            'atmos_alt': 'Tate Modern and the south bank in haze — the river',
            'atmos_credit': 'Peter Grecian',
            'tip': 'Track 47 (the Maidens\' opening song) is one of Wagner\'s most beautiful lyric passages. Savour the pure Rhine music before human drama returns.',
            'playlist': 'PLeMsytZrLIuaVkM4mbNv8MtSq0wFWhfNS',
        },
        {
            'num': 11, 'title': 'Hunt, Narration & Murder', 'act': 'Act 3',
            'tracks': '53–58', 'duration': '19:12',
            'location': 'Forest clearing',
            'characters': 'Siegfried, Hagen, Gunther, Vassals',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/a/aa/Siegfried_and_the_Twilight_of_the_Gods_p_172.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; Siegfried\'s death',
            'synopsis': 'Midday rest during the hunt. Hagen suggests Siegfried tell his life story. He narrates his youth — Mime, reforging Nothung, killing Fafner, understanding birdsong. The orchestra replays the entire Siegfried opera in miniature. Then he stops: memory ends where the potion took hold. Hagen hands him a drink — <em>"this will refresh your memory."</em> Siegfried\'s face changes. Memory floods back: <em>"Brünnhilde! I remember! She woke, and we —"</em> Two ravens fly up. Hagen: <em>"Do you understand those ravens\' cries? They tell me: Revenge!"</em> He drives the spear into Siegfried\'s back. Siegfried\'s dying vision is of Brünnhilde: <em>"Holy bride! Awake! Open your eyes!"</em> He dies calling her name.',
            'performers': '',
            'context': 'Hagen\'s final sadism: restoring Siegfried\'s memory before killing him. He wants Siegfried to die knowing he betrayed Brünnhilde — even though the betrayal was involuntary. The murder would work without restored memory; Hagen adds it for personal satisfaction. This is the mark of Alberich\'s son: unnecessary malice. Yet Wagner grants mercy — Siegfried escapes the Gibichung world (lies, manipulation, politics) and returns in death to the mountain, the fire, the awakening.',
            'quote': '<em>"Brünnhilde! Heilige Braut! Wach auf! Offne dein Auge!"</em> — Brünnhilde! Holy bride! Awake! Open your eyes!',
            'musical': 'Siegfried\'s narration replays leitmotifs from the entire cycle — his life in music. The memory-restoring drink inverts the potion motif. Then the murder: a shocking orchestral blow. His 5-minute death scene builds from weakness to one transcendent burst of full-strength tenor, then fades. Listen for the orchestral silence — two full beats of nothing — before the Funeral March begins.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260305_153732877.MP.jpg',
            'atmos_alt': 'South London sprawl — the hunting ground',
            'atmos_credit': 'Peter Grecian',
            'tip': 'Track 57 contains memory restoration, ravens, and murder — all in 2:15. One of opera\'s most efficient catastrophes. Track 58 (the death) — Siegfried dies remembering love, not heroism. The orchestra weeps.',
            'playlist': 'PLeMsytZrLIubt28DLEYg3_7NmUWR1GSRL',
        },
        {
            'num': 12, 'title': "Funeral March, Immolation & End", 'act': 'Act 3',
            'tracks': '59–69', 'duration': '41:10',
            'location': 'Forest, Gibichung hall, and beyond',
            'characters': 'Orchestra, Gutrune, Hagen, Gunther, Brünnhilde',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/7/7f/Ring63.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; Brünnhilde leaps onto the funeral pyre',
            'synopsis': '<strong>Funeral March</strong> (Track 59, 6:14): The orchestra alone eulogises Siegfried — five phases recounting his youth, heroism, love, and loss. No words needed; the music <em>is</em> the biography. <strong>Aftermath</strong> (Tracks 60-63): Back at the hall, Hagen lies about a boar. Gunther reveals the truth. They fight over the Ring. Hagen kills Gunther. When Hagen reaches for the Ring, <strong>the corpse\'s hand rises</strong> — Hagen recoils in terror. The curse protects itself. <strong>Immolation</strong> (Tracks 64-69): Brünnhilde enters, silences everyone, and speaks with recovered divine authority. She orders the pyre, takes the Ring, understands Wotan\'s design at last: <em>"The world built on power and law is broken. Love alone redeems, but love requires sacrifice."</em> She returns the Ring to the Rhine, commands Loge to burn Valhalla, and rides Grane into the flames. The Rhine floods. The Rhine Maidens reclaim the gold. Hagen drowns reaching for it. Valhalla burns. The Redemption through Love motif rises — ascending, radiant. The orchestra holds the final chord. Curtain.',
            'performers': '<strong>Anne Evans</strong> — Her Immolation is intelligently paced, emphasising text clarity. Her final <em>"Siegfried!"</em> has genuine joy — not despair.',
            'context': 'Brünnhilde\'s final understanding: Wotan needed a free hero (Siegfried) and a free woman (herself) to make the choice he could not command. Only free will — unconstrained by divine law — can truly redeem. The Ring cycle ends where it began: at the Rhine. The gold is returned, the curse lifted, the gods gone. Whether this is tragedy or hope — whether the cycle repeats or humanity learns — Wagner leaves unanswered. <em>The music resolves. The story does not.</em>',
            'quote': '<em>"Ruhe, ruhe, du Gott!"</em> — Rest, rest, you god!',
            'musical': 'Every major leitmotif from all four Ring operas returns: Rhine, Valhalla, Ring curse, Alberich\'s renunciation, Brünnhilde\'s love, Siegfried\'s horn, forest murmurs, Norns, immolation, and finally Redemption through Love — ascending D-flat major, strings shimmering. Musical architecture on an unprecedented scale.',
            'tip': 'Track 59 (Funeral March) is arguably Wagner\'s single greatest orchestral passage — listen with no distractions. The final 90 seconds of Track 69: the Redemption through Love motif was hinted at throughout 15+ hours of music; here it finally, fully, resolves.',
            'playlist': 'PLeMsytZrLIuYZv3LbHwFiEoBxfsxXN2QH',
        },
    ]

    # Group by act
    acts = {}
    for s in scenes:
        acts.setdefault(s['act'], []).append(s)

    # Build table of contents
    toc_html = '<nav class="toc"><div class="toc-title">Contents</div>\n'
    for act_name in ['Prologue', 'Act 1', 'Act 2', 'Act 3']:
        act_id = act_name.lower().replace(' ', '')
        toc_html += f'<div class="toc-act">{act_name}</div>\n'
        for s in acts.get(act_name, []):
            toc_html += f'<a class="toc-scene" href="#scene-{s["num"]}">{s["num"]}. {s["title"]}</a>\n'
    toc_html += '</nav>\n'

    cards_html = ''
    for act_name in ['Prologue', 'Act 1', 'Act 2', 'Act 3']:
        act_id = act_name.lower().replace(' ', '')
        # Inline mini-TOC before Act 2 and Act 3
        if act_name in ('Act 2', 'Act 3'):
            mini = '<nav class="toc mini-toc">\n'
            for a in ['Prologue', 'Act 1', 'Act 2', 'Act 3']:
                current = ' style="color:var(--text);font-weight:600"' if a == act_name else ''
                mini += f'<span class="toc-act">{a}</span>\n'
                for sc in acts.get(a, []):
                    mini += f'<a class="toc-scene"{current if a == act_name else ""} href="#scene-{sc["num"]}">{sc["num"]}. {sc["title"]}</a>\n'
            mini += '</nav>\n'
            cards_html += mini
        cards_html += f'<h2 class="act-heading" id="{act_id}">{act_name}</h2>\n'
        for s in acts.get(act_name, []):
            ytm_url = f"https://music.youtube.com/playlist?list={s['playlist']}"
            performers_html = f'<details class="scene-details"><summary>The performers</summary><div class="performers-content">{s["performers"]}</div></details>' if s.get('performers') else ''
            atmos_html = f'<div class="scene-img atmos"><img src="{s["atmos_img"]}" alt="{s["atmos_alt"]}" loading="lazy"><span class="img-credit">{s["atmos_credit"]}</span></div>' if s.get('atmos_img') else ''
            cards_html += f'''<div class="scene-card" id="scene-{s['num']}">
  <div class="scene-header">
    <div class="scene-num">{s['num']}</div>
    <div class="scene-info">
      <div class="scene-title">{s['title']}</div>
      <div class="scene-meta">Tracks {s['tracks']} &middot; {s['duration']} &middot; {s['location']}</div>
      <div class="scene-chars">{s['characters']}</div>
    </div>
    <a href="{ytm_url}" target="_blank" class="ytm-btn" title="Play on YouTube Music">&#9654;</a>
  </div>
  <div class="scene-img"><img src="{s['img']}" alt="{s['title']}" loading="lazy"><span class="img-credit">{s['img_credit']}</span></div>
  {atmos_html}
  <p class="scene-synopsis">{s['synopsis']}</p>
  <blockquote class="scene-quote">{s['quote']}</blockquote>
  {performers_html}
  <details class="scene-details"><summary>Dramatic context</summary><p>{s['context']}</p></details>
  <details class="scene-details"><summary>Musical features</summary><p>{s['musical']}</p></details>
  <details class="scene-details"><summary>Listening tip</summary><p>{s['tip']}</p></details>
</div>
'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gotterdammerung on the Go</title>
  <link rel="icon" type="image/png" sizes="192x192" href="https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/icon-192.png">
  <link rel="manifest" href="/gotg/manifest.json">
  <meta name="theme-color" content="#000000">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <link rel="apple-touch-icon" href="https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/icon-192.png">
  {THEME_CSS_JS}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 700px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1.5rem 0 0.3rem; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.3rem; }}
    .recording-info {{ background: var(--card-bg); border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.6; }}
    .recording-info a {{ color: var(--accent); text-decoration: none; }}
    .recording-info strong {{ color: var(--text); }}
    .rec-photos {{ display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }}
    .rec-photo {{ flex: 1; border-radius: 8px; overflow: hidden; position: relative; }}
    .rec-photo img {{ width: 100%; height: 140px; object-fit: cover; display: block; }}
    .toc {{ background: var(--card-bg); border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 1.5rem; }}
    .mini-toc {{ margin-top: 2rem; }}
    .toc-title {{ font-weight: 600; font-size: 0.9rem; color: var(--text); margin-bottom: 0.5rem; }}
    .toc-act {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.5rem; font-weight: 600; }}
    .toc-scene {{ display: block; font-size: 0.8rem; color: var(--accent); text-decoration: none; padding: 0.15rem 0 0.15rem 0.8rem; }}
    .toc-scene:hover {{ opacity: 0.7; }}
    .act-heading {{ color: var(--accent); font-size: 1.1rem; margin: 1.5rem 0 0.5rem; padding-bottom: 0.3rem; border-bottom: 1px solid var(--divider); }}
    .scene-card {{ background: var(--card-bg); border-radius: 12px; padding: 1rem; margin-bottom: 0.75rem; }}
    .scene-header {{ display: flex; align-items: flex-start; gap: 0.75rem; }}
    .scene-num {{ font-size: 1.4rem; font-weight: 700; color: var(--accent); min-width: 1.8rem; text-align: center; line-height: 1.2; }}
    .scene-info {{ flex: 1; min-width: 0; }}
    .scene-title {{ font-size: 1rem; font-weight: 600; }}
    .scene-meta {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.15rem; }}
    .scene-chars {{ font-size: 0.75rem; color: var(--text-secondary); font-style: italic; margin-top: 0.1rem; }}
    .ytm-btn {{ display: flex; align-items: center; justify-content: center; width: 2.4rem; height: 2.4rem; border-radius: 50%; background: #FF0000; color: #fff; text-decoration: none; font-size: 1rem; flex-shrink: 0; margin-top: 0.2rem; }}
    .ytm-btn:hover {{ opacity: 0.85; }}
    .scene-img {{ margin: 0.6rem 0 0; border-radius: 8px; overflow: hidden; position: relative; }}
    .scene-img img {{ width: 100%; height: auto; display: block; opacity: 0.85; }}
    .scene-img.atmos img {{ height: 160px; object-fit: cover; opacity: 0.7; }}
    .img-credit {{ position: absolute; bottom: 0; right: 0; background: rgba(0,0,0,0.7); color: #aaa; font-size: 0.65rem; padding: 0.15rem 0.4rem; border-radius: 8px 0 0 0; }}
    .perf-photo {{ float: right; width: 80px; height: 100px; object-fit: cover; border-radius: 6px; margin: 0 0 0.4rem 0.6rem; opacity: 0.9; }}
    .performers-content {{ font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; margin: 0.3rem 0 0; overflow: hidden; }}
    .scene-synopsis {{ font-size: 0.85rem; line-height: 1.55; margin: 0.6rem 0 0.3rem; color: var(--text); }}
    .scene-quote {{ margin: 0.4rem 0; padding: 0.4rem 0.8rem; border-left: 3px solid var(--accent); font-style: italic; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; }}
    .scene-details {{ margin-top: 0.3rem; }}
    .scene-details summary {{ font-size: 0.8rem; color: var(--accent); cursor: pointer; padding: 0.2rem 0; }}
    .scene-details p {{ font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; margin: 0.3rem 0 0; }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Gotterdammerung on the Go</h1>
    <div class="subtitle">Scene-by-scene listening guide &middot; 12 playlists &middot; 69 tracks</div>
    <div class="recording-info">
      <div class="rec-photos">
        <div class="rec-photo"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Festspielhaus_Bayreuth_001.jpg/400px-Festspielhaus_Bayreuth_001.jpg" alt="Bayreuth Festspielhaus" loading="lazy"><span class="img-credit">DALIBRI, CC BY-SA 4.0</span></div>
        <div class="rec-photo"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Daniel_Barenboim_%40_Staatsoper_f%C3%BCr_alle_2014_cropped.jpg/300px-Daniel_Barenboim_%40_Staatsoper_f%C3%BCr_alle_2014_cropped.jpg" alt="Daniel Barenboim" loading="lazy"><span class="img-credit">Sebaso, CC BY-SA 3.0</span></div>
      </div>
      <strong>The Recording:</strong> Daniel Barenboim conducting the Bayreuth Festival Orchestra, 1991. Staged by Harry Kupfer. Recorded live in the Festspielhaus (above left), the theatre Wagner designed specifically for his operas — the orchestra plays from a covered pit, invisible to the audience, producing a uniquely blended sound.
      <br><br>
      <strong>Bayreuth</strong> is a small Franconian town in northern Bavaria where Wagner built his Festspielhaus in 1876. The annual festival draws audiences from around the world, with waiting lists stretching years. This recording captures one of the great modern Ring cycles — Barenboim\'s brisk tempi emphasise forward drama over lingering Romanticism.
      <br><br>
      <a href="https://music.youtube.com/playlist?list=OLAK5uy_k-904jYLqH1bXAkGMbdNvMJPL9zbKbCsM" target="_blank">Full album on YouTube Music</a> &middot; Total duration: approx. 4 hours 20 minutes
    </div>
{toc_html}
{cards_html}
    <div class="footer">
      Artwork: Arthur Rackham (1910-11), public domain. Performer/venue photos: Wikimedia Commons (CC BY-SA). Atmosphere photos: Peter Grecian.<br>
      <a href="/contents">Home</a>
    </div>
  </div>
<script>
(function(){{
  var creditsOn=localStorage.getItem('gotg-credits')!=='off';
  function apply(){{document.querySelectorAll('.img-credit').forEach(function(el){{el.style.display=creditsOn?'':'none';}});}}
  apply();
  var mo=new MutationObserver(apply);
  mo.observe(document.body,{{childList:true,subtree:true}});
  function addMenuItem(){{
    var menu=window._settingsMenu;
    if(!menu)return;
    var item=document.createElement('div');
    item.className='settings-item';
    var label=document.createElement('span');
    label.textContent='Photo credits';
    var check=document.createElement('span');
    check.className='check';
    function upd(){{check.textContent=creditsOn?'\u2713':'';}}
    upd();
    item.appendChild(label);
    item.appendChild(check);
    item.onclick=function(e){{
      e.stopPropagation();
      creditsOn=!creditsOn;
      localStorage.setItem('gotg-credits',creditsOn?'on':'off');
      upd();apply();
    }};
    menu.appendChild(item);
  }}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',addMenuItem);
  else addMenuItem();
}})();
</script>
</body>
</html>'''


def render_site_test_page():
    """Render the site test page - tests all pages and shows load times and status."""
    return f'''<html lang="en">
  <head>
    <title>Site Test - Page Load Times and Status</title>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      body {{ font-family: var(--font); background: var(--bg); color: var(--text); min-height: 100vh; padding: 2rem; }}
      .container {{ max-width: 1000px; margin: 0 auto; }}
      h1 {{ color: var(--text); text-align: center; margin-bottom: 0.5rem; }}
      .nav {{ text-align: center; margin-bottom: 2rem; }}
      .nav a {{ color: var(--accent); text-decoration: none; background: var(--card-bg); border: 1px solid var(--divider); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; display: inline-block; transition: opacity 0.2s; }}
      .nav a:hover {{ opacity: 0.8; }}
      .subtitle {{ color: var(--text-secondary); text-align: center; margin-bottom: 2rem; font-size: 0.95rem; }}
      .table-wrapper {{ background: var(--card-bg); border-radius: 12px; overflow: hidden; border: 1px solid var(--divider); }}
      table {{ width: 100%; border-collapse: collapse; }}
      thead {{ background: var(--divider); color: var(--text); }}
      th {{ padding: 1rem; text-align: left; font-weight: 600; color: var(--text); }}
      td {{ padding: 0.8rem 1rem; border-bottom: 1px solid var(--divider); color: var(--text); }}
      tbody tr:hover {{ background: rgba(142,142,147,0.1); }}
      .page-name {{ font-weight: 500; color: var(--text); }}
      .page-name a {{ color: var(--accent); text-decoration: none; }}
      .page-name a:hover {{ text-decoration: underline; }}
      .loading {{ color: var(--accent); font-style: italic; }}
      .success {{ color: #10b981; font-weight: 600; }}
      .error {{ color: var(--error); font-weight: 600; }}
      .timeout {{ color: var(--warning); font-weight: 600; }}
      .protected {{ color: var(--accent); font-weight: 600; }}
      .time {{ font-family: monospace; text-align: right; font-size: 0.9rem; color: var(--text-secondary); }}
      .controls {{ text-align: center; margin-bottom: 1.5rem; }}
      button {{ background: var(--card-bg); color: var(--accent); border: 1px solid var(--divider); padding: 0.8rem 1.5rem; border-radius: 20px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; font-size: 1rem; }}
      button:hover {{ opacity: 0.8; }}
      button:disabled {{ opacity: 0.4; cursor: not-allowed; }}
      .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 2rem; }}
      .stat-box {{ background: var(--card-bg); padding: 1.5rem; border-radius: 12px; text-align: center; border: 1px solid var(--divider); }}
      .stat-value {{ font-size: 2rem; font-weight: bold; color: var(--accent); }}
      .stat-label {{ color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.5rem; }}
    </style>
    {THEME_CSS_JS}
  </head>
  <body>
    <div class="container">
      <h1>Site Test</h1>
      <p class="subtitle">Page load times and status monitoring</p>
      <div class="nav">
        <a href="contents">← Home</a>
      </div>

      <div class="controls">
        <button id="testBtn" onclick="testAllPages()">Start Tests</button>
        <button id="resetBtn" onclick="resetTests()" style="margin-left: 1rem;">Reset</button>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Page</th>
              <th>Status</th>
              <th style="text-align: right;">Load Time</th>
            </tr>
          </thead>
          <tbody id="testResults"></tbody>
        </table>
      </div>

      <div class="stats">
        <div class="stat-box">
          <div class="stat-value" id="avgTime">—</div>
          <div class="stat-label">Avg Load Time</div>
        </div>
        <div class="stat-box">
          <div class="stat-value" id="successCount">0</div>
          <div class="stat-label">Successful</div>
        </div>
        <div class="stat-box">
          <div class="stat-value" id="protectedCount">0</div>
          <div class="stat-label">Protected</div>
        </div>
        <div class="stat-box">
          <div class="stat-value" id="errorCount">0</div>
          <div class="stat-label">Errors</div>
        </div>
      </div>
    </div>

    <script>
      const pages = [
        {{ id: 'cv', path: 'cv', label: 'CV / Curriculum Vitae' }},
        {{ id: 'pi-fleet', path: 'pi-fleet', label: 'Pi Fleet Status' }},
        {{ id: 'ai-config', path: 'ai-config', label: 'AI Configuration' }},
        {{ id: 't3', path: 't3', label: 'K2 Bus Times' }},
        {{ id: 'memspeed', path: 'memspeed', label: 'Memory Benchmark' }},
        {{ id: 'lambda-stats', path: 'lambda-stats', label: 'Lambda Statistics' }},
        {{ id: 'gardencam', path: 'gardencam', label: 'Garden Camera' }},
        {{ id: 'springcam', path: 'springcam', label: 'Spring Camera' }},
        {{ id: 'rcr', path: 'rcr', label: 'Recent Classical Recordings' }}
      ];

      // Build table rows from pages array
      const tbody = document.getElementById('testResults');
      pages.forEach(page => {{
        const tr = document.createElement('tr');
        tr.id = `row-${{page.id}}`;
        tr.innerHTML = `<td class="page-name"><a href="${{page.path}}" target="_blank">${{page.label}}</a></td><td class="loading">pending...</td><td class="time">—</td>`;
        tbody.appendChild(tr);
      }});

      async function testPage(page) {{
        const row = document.getElementById(`row-${{page.id}}`);
        const statusCell = row.cells[1];
        const timeCell = row.cells[2];

        try {{
          const startTime = performance.now();
          const response = await fetch(page.path, {{
            method: 'GET',
            signal: AbortSignal.timeout(10000) // 10 second timeout
          }});
          const endTime = performance.now();
          const loadTime = endTime - startTime;

          if (response.status === 200) {{
            statusCell.className = 'success';
            statusCell.textContent = '✓ OK';
            timeCell.textContent = loadTime.toFixed(0) + ' ms';
            return {{ status: 'success', time: loadTime }};
          }} else if (response.status === 401) {{
            statusCell.className = 'protected';
            statusCell.textContent = '🔒 Auth Required';
            timeCell.textContent = loadTime.toFixed(0) + ' ms';
            return {{ status: 'protected', time: loadTime }};
          }} else {{
            statusCell.className = 'error';
            statusCell.textContent = `✗ ${{response.status}}`;
            timeCell.textContent = loadTime.toFixed(0) + ' ms';
            return {{ status: 'error', time: loadTime }};
          }}
        }} catch (error) {{
          if (error.name === 'AbortError') {{
            statusCell.className = 'timeout';
            statusCell.textContent = '⏱ Timeout';
            timeCell.textContent = '10000+ ms';
            return {{ status: 'timeout', time: 10000 }};
          }} else {{
            statusCell.className = 'error';
            statusCell.textContent = error.message;
            timeCell.textContent = '—';
            return {{ status: 'error', time: 0 }};
          }}
        }}
      }}

      async function testAllPages() {{
        const btn = document.getElementById('testBtn');
        btn.disabled = true;
        btn.textContent = 'Testing...';

        const results = await Promise.all(pages.map(page => testPage(page)));

        // Update statistics
        const successful = results.filter(r => r.status === 'success').length;
        const protected_pages = results.filter(r => r.status === 'protected').length;
        const errors = results.filter(r => r.status === 'error' || r.status === 'timeout').length;
        const successfulTimes = results.filter(r => r.status === 'success').map(r => r.time);
        const avgTime = successfulTimes.length > 0 ? (successfulTimes.reduce((a, b) => a + b) / successfulTimes.length).toFixed(0) : '—';

        document.getElementById('successCount').textContent = successful;
        document.getElementById('protectedCount').textContent = protected_pages;
        document.getElementById('errorCount').textContent = errors;
        document.getElementById('avgTime').textContent = avgTime + (avgTime !== '—' ? ' ms' : '');

        btn.disabled = false;
        btn.textContent = 'Start Tests';
      }}

      function resetTests() {{
        document.querySelectorAll('tbody tr').forEach(row => {{
          const statusCell = row.cells[1];
          const timeCell = row.cells[2];
          statusCell.className = 'loading';
          statusCell.textContent = 'pending...';
          timeCell.textContent = '—';
        }});
        document.getElementById('avgTime').textContent = '—';
        document.getElementById('successCount').textContent = '0';
        document.getElementById('protectedCount').textContent = '0';
        document.getElementById('errorCount').textContent = '0';
      }}
    </script>
  </body>
</html>'''


AI_APPS = [
    {"key": "alerting", "name": "Alerting", "desc": "Incident analysis"},
    {"key": "rcr", "name": "RCR", "desc": "Album ranking"},
    {"key": "uvtm", "name": "Us vs Machines", "desc": "F1 predictions"},
]
AI_PROVIDERS = [
    {"key": "gemini", "name": "Gemini", "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]},
    {"key": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini"]},
    {"key": "bedrock", "name": "Bedrock", "models": ["anthropic.claude-3-5-sonnet-20241022-v2:0", "anthropic.claude-3-haiku-20240307-v1:0"]},
]


def get_ai_usage():
    """Read AI usage from DynamoDB for today and compute velocity metrics."""
    from decimal import Decimal
    dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
    table = dynamodb.Table("ai-usage")

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    try:
        resp = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("date").eq(today),
        )
        items = resp.get("Items", [])
    except Exception as e:
        print(f"Error reading ai-usage: {e}")
        return {"calls_today": 0, "calls_1m": 0, "calls_10m": 0, "by_app": {}, "recent": []}

    # Parse timestamps and compute windows
    calls = []
    for item in items:
        try:
            ts = datetime.fromisoformat(item["timestamp"])
            calls.append({
                "ts": ts,
                "app": item.get("app", "?"),
                "provider": item.get("provider", "?"),
                "model": item.get("model", "?"),
                "duration_ms": int(item.get("duration_ms", 0)),
                "error": item.get("error"),
            })
        except Exception:
            pass

    calls.sort(key=lambda c: c["ts"], reverse=True)

    t1m = now - timedelta(minutes=1)
    t10m = now - timedelta(minutes=10)

    # Per-app breakdown across all 3 time windows
    app_keys = [a["key"] for a in AI_APPS]
    by_app = {}
    for ak in app_keys:
        app_calls = [c for c in calls if c["app"] == ak]
        by_app[ak] = {
            "1m": sum(1 for c in app_calls if c["ts"] >= t1m),
            "10m": sum(1 for c in app_calls if c["ts"] >= t10m),
            "today": len(app_calls),
        }

    return {
        "calls_today": len(calls),
        "calls_1m": sum(1 for c in calls if c["ts"] >= t1m),
        "calls_10m": sum(1 for c in calls if c["ts"] >= t10m),
        "by_app": by_app,
        "recent": calls[:10],
    }


def get_ai_configs():
    """Read all /ai-config/ parameters from SSM."""
    ssm = boto3.client("ssm", region_name="eu-west-1")
    configs = {}
    for app in AI_APPS:
        try:
            resp = ssm.get_parameter(Name=f"/ai-config/{app['key']}")
            configs[app["key"]] = json.loads(resp["Parameter"]["Value"])
        except Exception:
            configs[app["key"]] = {"provider": "gemini", "model": "gemini-2.5-pro"}
    return configs


def set_ai_config(app_key, provider, model):
    """Write an /ai-config/ parameter to SSM."""
    ssm = boto3.client("ssm", region_name="eu-west-1")
    ssm.put_parameter(
        Name=f"/ai-config/{app_key}",
        Value=json.dumps({"provider": provider, "model": model}),
        Type="String",
        Overwrite=True,
    )


def _render_usage_bar(label, sublabel, value, limit, color="var(--accent)"):
    """Render a Claude-style usage bar with label, progress bar, and percentage."""
    pct = min(100, int(value / limit * 100)) if limit > 0 else 0
    return f'''<div style="margin-bottom:0.8rem;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.2rem;">
            <div>
                <span style="font-size:0.7rem;font-weight:600;color:var(--text);">{label}</span>
                <div style="font-size:0.55rem;color:var(--text-secondary);">{sublabel}</div>
            </div>
            <span style="font-size:0.6rem;color:var(--text-secondary);">{pct}% used</span>
        </div>
        <div style="height:6px;background:var(--divider);border-radius:3px;overflow:hidden;">
            <div style="height:100%;width:{pct}%;background:{color};border-radius:3px;transition:width 0.3s;"></div>
        </div>
    </div>'''


def _render_usage_meter(usage):
    """Render the AI usage meter section with Claude-style bars and 3x3 app grid."""
    if not usage:
        return ""

    now = datetime.now(timezone.utc)

    # Overall progress bars (Claude-style)
    bars = _render_usage_bar("Today", now.strftime("%d %b %Y"), usage["calls_today"], max(usage["calls_today"], 50))
    bars += _render_usage_bar("Last 10 minutes", "Rolling window", usage["calls_10m"], max(usage["calls_10m"], 10))
    bars += _render_usage_bar("Last minute", "Rolling window", usage["calls_1m"], max(usage["calls_1m"], 5))

    # 3x3 grid: apps × time windows
    by_app = usage.get("by_app", {})
    grid_rows = ""
    for app in AI_APPS:
        ak = app["key"]
        app_data = by_app.get(ak, {"1m": 0, "10m": 0, "today": 0})
        grid_rows += f'''<tr>
            <td style="padding:0.3rem 0.4rem;font-size:0.65rem;color:var(--text);font-weight:500;">{app['name']}</td>
            <td style="padding:0.3rem;text-align:center;font-size:0.7rem;font-weight:600;color:var(--accent);">{app_data['1m']}</td>
            <td style="padding:0.3rem;text-align:center;font-size:0.7rem;font-weight:600;color:var(--accent);">{app_data['10m']}</td>
            <td style="padding:0.3rem;text-align:center;font-size:0.7rem;font-weight:600;color:var(--accent);">{app_data['today']}</td>
        </tr>'''

    grid = f'''<table style="width:100%;border-collapse:collapse;margin-top:0.5rem;">
        <thead><tr>
            <th style="text-align:left;padding:0.3rem 0.4rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">App</th>
            <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">1 min</th>
            <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">10 min</th>
            <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Today</th>
        </tr></thead>
        <tbody>{grid_rows}</tbody>
    </table>'''

    # Recent calls
    recent_rows = ""
    for c in usage["recent"]:
        time_str = c["ts"].strftime("%H:%M:%S")
        status = f'<span style="color:var(--error);">{c["error"][:30]}</span>' if c.get("error") else f'{c["duration_ms"]}ms'
        model_short = c["model"].split("/")[-1].replace("anthropic.", "")
        if len(model_short) > 20:
            model_short = model_short[:18] + ".."
        recent_rows += f'''<tr style="border-top:1px solid var(--divider);">
            <td style="padding:0.3rem;font-size:0.55rem;color:var(--text-secondary);">{time_str}</td>
            <td style="padding:0.3rem;font-size:0.55rem;">{c["app"]}</td>
            <td style="padding:0.3rem;font-size:0.55rem;color:var(--text-secondary);">{model_short}</td>
            <td style="padding:0.3rem;font-size:0.55rem;text-align:right;">{status}</td>
        </tr>'''

    recent_html = ""
    if recent_rows:
        recent_html = f'''<div style="margin-top:1rem;">
            <div style="font-size:0.65rem;font-weight:600;color:var(--text);margin-bottom:0.4rem;">Recent calls</div>
            <table style="width:100%;border-collapse:collapse;">
                <tbody>{recent_rows}</tbody>
            </table>
        </div>'''

    return f'''
        <h2 style="font-size:0.9rem;font-weight:600;margin:1.5rem 0 0.8rem 0;">Usage</h2>
        {bars}
        {grid}
        {recent_html}'''


def render_ai_config_page(configs, usage=None, message=None):
    """Render the AI configuration matrix page with usage meter."""
    msg_html = ""
    if message:
        msg_html = f'<div style="background:var(--accent);color:#fff;padding:0.6rem 1rem;border-radius:8px;margin-bottom:1rem;font-size:0.8rem;">{message}</div>'

    # Build the matrix rows
    rows = ""
    for app in AI_APPS:
        cfg = configs.get(app["key"], {})
        active_provider = cfg.get("provider", "")
        active_model = cfg.get("model", "")

        cells = ""
        for prov in AI_PROVIDERS:
            is_active = prov["key"] == active_provider
            bg = "var(--accent)" if is_active else "var(--card-bg)"
            color = "#fff" if is_active else "var(--text-secondary)"
            border = "none" if is_active else "1px solid var(--divider)"

            # Model selector (shown below the button when active)
            model_opts = ""
            for m in prov["models"]:
                sel = " selected" if m == active_model else ""
                short = m.split("/")[-1].replace("anthropic.", "")
                model_opts += f'<option value="{m}"{sel}>{short}</option>'

            model_select = ""
            if is_active:
                model_select = f'''<select name="model" form="form-{app['key']}-{prov['key']}"
                    style="margin-top:0.3rem;width:100%;background:var(--bg);color:var(--text);border:1px solid var(--divider);border-radius:6px;padding:0.15rem;font-size:0.5rem;font-family:var(--font);"
                    onchange="this.form.submit()">{model_opts}</select>'''

            cells += f'''<td style="padding:0.4rem;text-align:center;vertical-align:top;">
                <form id="form-{app['key']}-{prov['key']}" method="POST" action="ai-config">
                    <input type="hidden" name="app" value="{app['key']}">
                    <input type="hidden" name="provider" value="{prov['key']}">
                    <input type="hidden" name="model" value="{prov['models'][0]}">
                    <button type="submit" style="background:{bg};color:{color};border:{border};border-radius:6px;padding:0.3rem 0.5rem;font-size:0.6rem;cursor:pointer;font-family:var(--font);width:100%;min-width:3.5rem;">{prov['name']}</button>
                </form>
                {model_select}
            </td>'''

        rows += f'''<tr>
            <td style="padding:0.4rem;font-size:0.7rem;white-space:nowrap;">
                <div style="color:var(--text);font-weight:600;">{app['name']}</div>
                <div style="color:var(--text-secondary);font-size:0.55rem;">{app['desc']}</div>
            </td>
            {cells}
        </tr>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Configuration</title>
    {THEME_CSS_JS}
</head>
<body style="margin:0;padding:1rem;background:var(--bg);color:var(--text);font-family:var(--font);">
    <div style="max-width:600px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:1rem;">
            <a href="contents" style="color:var(--accent);text-decoration:none;font-size:0.75rem;">Home</a>
        </div>
        <h1 style="font-size:1rem;font-weight:600;margin:0 0 0.8rem 0;text-align:center;">AI Configuration</h1>
        {msg_html}
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="text-align:left;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">App</th>
                    <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Gemini</th>
                    <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">OpenAI</th>
                    <th style="text-align:center;padding:0.3rem;color:var(--text-secondary);font-size:0.55rem;font-weight:500;">Bedrock</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        {_render_usage_meter(usage)}
    </div>
</body>
</html>'''


def lambda_handler(event, context):
    import time
    start_time = time.time()

    # Log connection details to DynamoDB
    log_connection(event, context)

    html = ""
    try:
        favicon = open("favicon.png64", "r").read()
        fav = f'<link rel="icon" type="image/png" href="data:image/png;base64,{favicon}">'
    except FileNotFoundError:
        fav = ""
    #fav += '\n<head><link rel="stylesheet" href="styles.css"></head>'

    # Handle both REST API and HTTP API (v2) event formats
    if 'rawPath' in event:
        # HTTP API v2 format
        path = event['rawPath']
        stage = event.get('requestContext', {}).get('stage', 'default')
        host = event.get('headers', {}).get('host', '')
    else:
        # REST API format
        path = event['path']
        stage = event['requestContext']['stage']
        host = event['headers']['Host']
    root=f'https://{host}/{stage}'
    print(f'path = {path}, stage = {stage}, root = {root}')
    try:
        ref = event['headers']['referer']
        print(f'referer = {ref}')
    except KeyError:
        pass
    # Handle different header formats
    headers = event.get('headers', {})
    ip = headers.get('X-Forwarded-For') or headers.get('x-forwarded-for', 'Unknown')
    print(f'X-Forwarded-For = {ip}')

    # robots.txt — reduce bot traffic and unnecessary invocations
    if path == f'/{stage}/robots.txt' or path == '/robots.txt':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/plain'},
            'body': (
                'User-agent: *\n'
                'Allow: /\n'
                'Allow: /cv\n'
                'Allow: /contents\n'
                'Disallow: /event\n'
                'Disallow: /gitinfo\n'
                'Disallow: /lambda-stats\n'
                'Disallow: /gardencam\n'
                'Disallow: /memspeed\n'
                'Disallow: /pi-fleet\n'
                'Disallow: /t3\n'
                'Disallow: /rcr\n'
                'Disallow: /us-vs-the-machines\n'
                'Disallow: /ai-config\n'
            )
        }

    if path == f'/{stage}/event' or path == '/event':   # debugging info
        html += '<div style="text-align: center; margin: 1rem;"><a href="contents" style="color: #4a9eff; text-decoration: none;">Home</a></div>'
        html += 'log_group = ' + context.log_group_name + '<br>'
        html += 'log_stream = ' + context.log_stream_name + '<br>' 
        html += 'path = ' + path + '<br>'
        html += 'stage = ' + stage + '<br>'
        html += 'root = ' + root + '<br>'
        html += 'pwd = ' + os.getcwd() + '<br>'
        for ff in os.listdir(os.getcwd()):
            html += ff + ', '
        html += '<br>'
        for key in event.keys():
            html += "_______________________" + key + "_________________________<br>"
            html += pformat(event[key]).replace(',', ',<br>') + "<br><br>"
    elif path == f'/{stage}/gitinfo' or path == '/gitinfo':
        html = open("gitinfo.html", "r").read()
    elif path == f'/{stage}/cv' or path == '/cv':
        html += open('cv.html', 'r').read()
    elif path == f'/{stage}/contents' or path == '/contents':
        html += render_contents_page()
    elif path == f'/{stage}/site-test' or path == '/site-test':
        html = render_site_test_page()
    elif path.startswith(f'/{stage}/gardencam/capture') or path.startswith('/gardencam/capture'):
        # Capture command endpoint
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Write command to DynamoDB
        try:
            dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
            table = dynamodb.Table('gardencam-commands')

            command_id = f"capture_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            item = {
                'command_id': command_id,
                'command': 'take_picture',
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'requested_by': event['headers'].get('X-Forwarded-For', 'unknown')
            }

            table.put_item(Item=item)

            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Capture command sent! Image will appear shortly.', 'command_id': command_id}),
                'headers': {'Content-Type': 'application/json'}
            }
        except Exception as e:
            print(f"Error writing capture command: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to send capture command'}),
                'headers': {'Content-Type': 'application/json'}
            }

    elif path.startswith(f'/{stage}/gardencam/timing') or path.startswith('/gardencam/timing'):
        # Page load timing endpoint
        if method == 'POST':
            try:
                from decimal import Decimal

                body = event.get('body', '{}')
                timing_data = json.loads(body)

                # Log to DynamoDB
                if BOTO3_AVAILABLE:
                    dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
                    table = dynamodb.Table('gardencam-page-timing')

                    item = {
                        'timestamp': timing_data.get('timestamp', datetime.utcnow().isoformat()),
                        'page_load_ms': Decimal(str(timing_data.get('pageLoadTime', 0))),
                        'dom_ready_ms': Decimal(str(timing_data.get('domReadyTime', 0))),
                        'server_response_ms': Decimal(str(timing_data.get('serverResponseTime', 0))),
                        'user_agent': timing_data.get('userAgent', '')[:500],
                        'ip': event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
                    }

                    table.put_item(Item=item)

                return {
                    'statusCode': 200,
                    'body': json.dumps({'status': 'logged'}),
                    'headers': {'Content-Type': 'application/json'}
                }
            except Exception as e:
                print(f"Error logging timing: {e}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': str(e)}),
                    'headers': {'Content-Type': 'application/json'}
                }

    elif path.startswith(f'/{stage}/gardencam/stats') or path.startswith('/gardencam/stats'):
        # Stats visualization page
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Fetch more stats to ensure we have enough data for 8 days
        stats = get_gardencam_stats(limit=2000)

        # Get current time and define 8 time windows (last 24h + 7 previous days)
        now = datetime.now(timezone.utc)

        # Define 8 windows: today (last 24h), yesterday, day before, etc.
        windows = []
        for i in range(8):
            window_end = now - timedelta(days=i)
            window_start = window_end - timedelta(days=1)
            windows.append({
                'start': window_start,
                'end': window_end,
                'label': f'{window_start.strftime("%Y-%m-%d")} to {window_end.strftime("%Y-%m-%d")}' if i > 0 else 'Last 24 Hours',
                'data': []
            })

        # Group stats into windows
        for item in stats:
            ts_str = item.get('timestamp', '')
            if not ts_str:
                continue

            try:
                # Parse ISO timestamp
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                # Find which window this belongs to
                for window in windows:
                    if window['start'] <= ts < window['end']:
                        window['data'].append({
                            'timestamp': ts,
                            'timestamp_str': ts.strftime('%H:%M'),
                            'avg_brightness': float(item.get('avg_brightness', 0)),
                            'mode': item.get('mode', 'unknown')
                        })
                        break
            except Exception as e:
                print(f"Error parsing timestamp {ts_str}: {e}")
                continue

        # Sort data within each window by timestamp
        for window in windows:
            window['data'].sort(key=lambda x: x['timestamp'])

        # Calculate summary stats
        total_images = sum(len(w['data']) for w in windows)
        all_modes = [d['mode'] for w in windows for d in w['data']]
        day_count = sum(1 for m in all_modes if m == 'day')
        night_count = sum(1 for m in all_modes if m == 'night')
        stacking_count = sum(1 for m in all_modes if m == 'stacking')
        all_brightness = [d['avg_brightness'] for w in windows for d in w['data']]
        avg_brightness = sum(all_brightness) / len(all_brightness) if all_brightness else 0

        html += f'''
        <title>Garden Camera Statistics</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .nav a:hover {{ background: #3a3a3a; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .chart-container {{ max-width: 1400px; margin: 0 auto 2rem auto; background: #2a2a2a; padding: 1.5rem; border-radius: 8px; }}
            .chart-title {{ font-size: 1.1rem; margin-bottom: 1rem; color: #aaa; text-align: center; }}
            .chart-subtitle {{ font-size: 0.9rem; color: #666; text-align: center; margin-top: -0.5rem; margin-bottom: 1rem; }}
            canvas {{ max-height: 300px; }}
            .stats-summary {{ max-width: 1400px; margin: 0 auto 2rem auto; padding: 1rem; background: #2a2a2a; border-radius: 8px; }}
            .stats-summary h2 {{ margin-top: 0; color: #aaa; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
            .stat-box {{ background: #1a1a1a; padding: 1rem; border-radius: 6px; text-align: center; }}
            .stat-value {{ font-size: 2rem; font-weight: bold; color: #4a9eff; }}
            .stat-label {{ color: #888; margin-top: 0.5rem; }}
            .legend {{ text-align: center; margin-bottom: 1rem; }}
            .legend-item {{ display: inline-block; margin: 0 1rem; }}
            .legend-color {{ display: inline-block; width: 20px; height: 20px; border-radius: 4px; vertical-align: middle; margin-right: 0.5rem; }}
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="gallery">Gallery</a>
            <a href="videos">Videos</a>
            <a href="s3-stats">Storage</a>
        </div>
        <h1>Garden Camera Statistics</h1>

        <div class="stats-summary">
            <h2>Summary (Last 8 Days)</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{total_images}</div>
                    <div class="stat-label">Total Images</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{day_count}</div>
                    <div class="stat-label">Day Mode</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{night_count}</div>
                    <div class="stat-label">Night Mode</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{stacking_count}</div>
                    <div class="stat-label">Stacking Mode</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{avg_brightness:.1f}</div>
                    <div class="stat-label">Avg Brightness</div>
                </div>
            </div>
        </div>

        <div class="legend">
            <div class="legend-item">
                <span class="legend-color" style="background: #f59e0b;"></span>
                <span>Day Mode</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #3b82f6;"></span>
                <span>Night Mode</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #8b5cf6;"></span>
                <span>Stacking Mode</span>
            </div>
        </div>
        '''

        # Create a chart for each window
        for i, window in enumerate(windows):
            if not window['data']:
                continue

            # Separate data by mode for color coding
            day_data = []
            night_data = []
            stacking_data = []
            labels = []

            for d in window['data']:
                labels.append(d['timestamp_str'])
                if d['mode'] == 'day':
                    day_data.append(d['avg_brightness'])
                    night_data.append(None)
                    stacking_data.append(None)
                elif d['mode'] == 'stacking':
                    day_data.append(None)
                    night_data.append(None)
                    stacking_data.append(d['avg_brightness'])
                else:  # night mode
                    day_data.append(None)
                    night_data.append(d['avg_brightness'])
                    stacking_data.append(None)

            chart_id = f'chart_{i}'
            data_count = len(window['data'])

            html += f'''
        <div class="chart-container">
            <div class="chart-title">{window['label']}</div>
            <div class="chart-subtitle">{data_count} images</div>
            <canvas id="{chart_id}"></canvas>
        </div>
            '''

        # Add JavaScript to create all charts
        html += '''
        <script>
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: {
                    ticks: { color: '#888', maxTicksLimit: 12 },
                    grid: { color: '#333' }
                },
                y: {
                    min: 0,
                    max: 255,
                    ticks: { color: '#888' },
                    grid: { color: '#333' },
                    title: {
                        display: true,
                        text: 'Uncorrected Brightness',
                        color: '#aaa'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            return 'Brightness: ' + context.parsed.y.toFixed(1);
                        }
                    }
                }
            },
            elements: {
                point: {
                    radius: 3,
                    hoverRadius: 6
                },
                line: {
                    borderWidth: 2
                }
            }
        };
        '''

        # Generate chart creation code for each window
        for i, window in enumerate(windows):
            if not window['data']:
                continue

            # Separate data by mode
            day_data = []
            night_data = []
            stacking_data = []
            labels = []

            for d in window['data']:
                labels.append(d['timestamp_str'])
                if d['mode'] == 'day':
                    day_data.append(d['avg_brightness'])
                    night_data.append(None)
                    stacking_data.append(None)
                elif d['mode'] == 'stacking':
                    day_data.append(None)
                    night_data.append(None)
                    stacking_data.append(d['avg_brightness'])
                else:  # night mode
                    day_data.append(None)
                    night_data.append(d['avg_brightness'])
                    stacking_data.append(None)

            chart_id = f'chart_{i}'

            html += f'''
        new Chart(document.getElementById('{chart_id}'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [
                    {{
                        label: 'Day',
                        data: {json.dumps(day_data)},
                        borderColor: '#f59e0b',
                        backgroundColor: '#f59e0b',
                        spanGaps: false
                    }},
                    {{
                        label: 'Night',
                        data: {json.dumps(night_data)},
                        borderColor: '#3b82f6',
                        backgroundColor: '#3b82f6',
                        spanGaps: false
                    }},
                    {{
                        label: 'Stacking',
                        data: {json.dumps(stacking_data)},
                        borderColor: '#8b5cf6',
                        backgroundColor: '#8b5cf6',
                        spanGaps: false
                    }}
                ]
            }},
            options: chartOptions
        }});
            '''

        html += '''
        </script>
        '''
    elif path.startswith(f'/{stage}/gardencam/fullres') or path.startswith('/gardencam/fullres'):
        # Full resolution image view
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Get image key from query string
        query_params = event.get('queryStringParameters', {}) or {}
        image_key = query_params.get('key', '')

        if image_key:
            timestamp = parse_timestamp_from_key(image_key) or 'Unknown'
            image_url = get_presigned_url(image_key)

            # Fetch stats for this image
            stats = get_image_stats_by_filename(image_key)
            stats_display = format_stats_for_display(stats)

            html += f'''
            <title>Full Resolution - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ margin-bottom: 1rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; }}
                .nav a:hover {{ text-decoration: underline; }}
                h2 {{ margin-bottom: 1rem; color: #aaa; }}
                img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a> | <a href="../gardencam">Latest</a> | <a href="gallery">Gallery</a>
            </div>
            <h2>{timestamp} UTC{stats_display}</h2>
            <img src="{image_url}" alt="Full resolution image">
            '''
        else:
            html += '<h1>Error: No image specified</h1>'
    elif path.startswith(f'/{stage}/gardencam/display') or path.startswith('/gardencam/display'):
        # Display-width image view
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Get image key from query string
        query_params = event.get('queryStringParameters', {}) or {}
        image_key = query_params.get('key', '')

        if image_key:
            timestamp = parse_timestamp_from_key(image_key) or 'Unknown'
            image_url = get_presigned_url(image_key)

            # Fetch stats for this image
            stats = get_image_stats_by_filename(image_key)
            stats_display = format_stats_for_display(stats)

            html += f'''
            <title>Display Width - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ margin-bottom: 1rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; }}
                .nav a:hover {{ text-decoration: underline; }}
                h2 {{ margin-bottom: 1rem; color: #aaa; }}
                .image-container {{ max-width: 1920px; margin: 0 auto; }}
                img {{ width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a> | <a href="../gardencam">Latest</a> | <a href="gallery">Gallery</a> | <a href="fullres?key={image_key}">Full Res</a>
            </div>
            <h2>{timestamp} UTC{stats_display}</h2>
            <div class="image-container">
                <a href="fullres?key={image_key}">
                    <img src="{image_url}" alt="Display width image">
                </a>
            </div>
            '''
        else:
            html += '<h1>Error: No image specified</h1>'
    elif path.startswith(f'/{stage}/gardencam/gallery') or path.startswith('/gardencam/gallery'):
        # Gallery page with thumbnails organized by weeks
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        week_param = query_params.get('week', '')
        day_param = query_params.get('day', '')

        # Three-level navigation: Weeks → Days → Images
        # OPTIMIZED: Only load S3 data when needed
        if not week_param:
            # Week index - generate deterministically, NO S3 queries
            weeks = generate_week_list()

            html += '''
            <title>Garden Camera Gallery - Weekly Index</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }
                .nav { text-align: center; margin-bottom: 2rem; }
                .nav a { color: #4a9eff; text-decoration: none; margin: 0 1rem; }
                .nav a:hover { text-decoration: underline; }
                h1 { text-align: center; margin-bottom: 2rem; }
                .week-list { max-width: 800px; margin: 0 auto; }
                .week-link { display: block; padding: 1rem 1.5rem; margin-bottom: 0.75rem; background: #2a2a2a; border-radius: 8px; text-decoration: none; color: #4a9eff; font-size: 1.1rem; transition: background 0.3s; }
                .week-link:hover { background: #3a3a3a; }
                .week-count { float: right; color: #888; font-size: 0.9rem; }
            </style>
            <div class="nav">
                <a href="../../contents">Home</a>
                <a href="../gardencam">Latest</a>
                <a href="videos">Videos</a>
                <a href="stats">Statistics</a>
            </div>
            <h1>Garden Camera Gallery - By Week</h1>
            <div class="week-list">
            '''

            for week_name in weeks:
                # Just show the week - no counting, no S3 queries
                html += f'''
                <a href="gallery?week={week_name}" class="week-link">
                    {week_name}
                </a>
                '''

            html += '</div>'

        elif week_param and not day_param:
            # Show days in the selected week - OPTIMIZED: only load images for this week
            current_week_images = get_images_for_week(week_param)

            if not current_week_images:
                html += '<h1>Week not found</h1><p><a href="gallery">Back to Gallery Index</a></p>'
            else:
                # Group week's images by day
                days = group_images_by_days(current_week_images)

                html += f'''
                <title>{week_param} - Days</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                    .nav {{ text-align: center; margin-bottom: 2rem; }}
                    .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; }}
                    .nav a:hover {{ text-decoration: underline; }}
                    h1 {{ text-align: center; margin-bottom: 2rem; }}
                    .day-list {{ max-width: 800px; margin: 0 auto; }}
                    .day-link {{ display: block; padding: 1rem 1.5rem; margin-bottom: 0.75rem; background: #2a2a2a; border-radius: 8px; text-decoration: none; color: #4a9eff; font-size: 1.1rem; transition: background 0.3s; }}
                    .day-link:hover {{ background: #3a3a3a; }}
                </style>
                <div class="nav">
                    <a href="../../contents">Home</a>
                    <a href="gallery">All Weeks</a>
                    <a href="../gardencam">Latest</a>
                </div>
                <h1>{week_param}</h1>
                <div class="day-list">
                '''

                for day_name, day_images in days:
                    html += f'''
                    <a href="gallery?week={week_param}&day={day_name}" class="day-link">
                        {day_name}
                    </a>
                    '''

                html += '</div>'

        else:
            # Show images for a specific day - OPTIMIZED: only fetch images for this day
            # Extract date from day_param: "2026-02-15 (Saturday)" → "2026-02-15"
            try:
                date_only = day_param.split(' ')[0]  # Get YYYY-MM-DD part
                current_day_images = get_images_for_date(date_only)
            except:
                current_day_images = []

            if not current_day_images:
                html += f'<h1>No images found for {day_param}</h1><p><a href="gallery?week={week_param}">Back to {week_param}</a></p>'
            else:
                # Get days in this week for prev/next navigation
                # Only load week data if needed for navigation
                current_week_images = get_images_for_week(week_param)
                days = group_images_by_days(current_week_images) if current_week_images else []
                day_index = None
                for idx, (day_name, _) in enumerate(days):
                    if day_name == day_param:
                        day_index = idx
                        break

                if day_index is None:
                    day_index = 0  # Fallback

                # Build navigation links
                prev_link = ''
                next_link = ''
                if day_index > 0:
                    prev_day = days[day_index - 1][0]
                    prev_link = f'<a href="gallery?week={week_param}&day={prev_day}">← Previous Day</a>'
                if day_index < len(days) - 1:
                    next_day = days[day_index + 1][0]
                    next_link = f'<a href="gallery?week={week_param}&day={next_day}">Next Day →</a>'

                html += f'''
                <title>{day_param} - Gallery</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                    .nav {{ text-align: center; margin-bottom: 1.5rem; }}
                    .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
                    .nav a:hover {{ background: #3a3a3a; }}
                    h1 {{ text-align: center; margin-bottom: 2rem; }}
                    .thumbnails {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; max-width: 1400px; margin: 0 auto; }}
                    .thumb-container {{ position: relative; }}
                    .thumb-container a {{ display: block; }}
                    .thumb-container img {{ width: 100%; height: 150px; object-fit: cover; border-radius: 6px; transition: transform 0.3s; box-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
                    .thumb-container img:hover {{ transform: scale(1.05); }}
                    .thumb-time {{ text-align: center; font-size: 0.85rem; color: #888; margin-top: 0.3rem; }}

                    @media (max-width: 768px) {{
                        .thumbnails {{ grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; }}
                        .thumb-container img {{ height: 120px; }}
                    }}
                </style>
                    <div class="nav">
                        <a href="../../contents">Home</a>
                        {prev_link}
                        <a href="gallery?week={week_param}">Week Index</a>
                        <a href="gallery">All Weeks</a>
                        <a href="../gardencam">Latest</a>
                        {next_link}
                    </div>
                    <h1>{day_param}</h1>
                '''

                html += '<div class="thumbnails">'

                displayed_count = 0
                displayed_images = []  # Track displayed images for delta calculation

                for img in current_day_images:
                    # Fetch stats for this image
                    stats = get_image_stats_by_filename(img['key'])

                    # Skip images that don't meet display criteria
                    if not should_display_image(stats):
                        continue

                    thumb_url = get_presigned_url(img['key'])
                    time_only = img['timestamp'].split()[1] if ' ' in img['timestamp'] else img['timestamp']
                    stats_display = format_stats_for_display(stats)

                    # Calculate time delta from previous displayed image
                    time_delta = ""
                    if displayed_images:
                        previous_img = displayed_images[-1]
                        time_delta = calculate_time_delta(img['timestamp'], previous_img['timestamp'])
                        if time_delta:
                            time_delta = f"{time_delta} "  # Add space after delta

                    html += f'''
                    <div class="thumb-container">
                        <a href="display?key={img['key']}">
                            <img src="{thumb_url}" alt="{img['timestamp']}">
                        </a>
                        <div class="thumb-time">{time_delta}{time_only}{stats_display}</div>
                    </div>
                    '''
                    displayed_count += 1
                    displayed_images.append(img)

                html += '</div>'

    elif path.startswith(f'/{stage}/gardencam/s3-stats') or path.startswith('/gardencam/s3-stats'):
        # S3 storage statistics page - reads from cached JSON
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Read cached summary from S3 (updated hourly by gardencam-storage-summary Lambda)
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        cache_key = "stats/s3-storage-summary.json"
        cache_error = None

        try:
            response = s3.get_object(Bucket=GARDENCAM_BUCKET, Key=cache_key)
            summary = json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            cache_error = str(e)
            summary = None

        if summary:
            # Extract data from cached summary
            total_files = summary.get('total_count', 0)
            total_size_gb = summary.get('total_size_gb', 0)
            costs = summary.get('costs', {})
            storage_cost = costs.get('monthly_storage_cost_usd', 0)
            put_cost = costs.get('monthly_put_cost_usd', 0)
            get_cost = costs.get('monthly_get_cost_usd', 0)
            total_monthly = costs.get('total_monthly_cost_usd', storage_cost)
            yearly_total = costs.get('yearly_total_cost_usd', total_monthly * 12)
            weekly_stats = summary.get('weekly_stats', {})
            generated_at = summary.get('generated_at', 'Unknown')

            # Sort weeks
            sorted_weeks = sorted(weekly_stats.items(), reverse=True)

            # Prepare chart data (last 12 weeks, oldest first)
            chart_weeks = []
            chart_counts = []
            chart_sizes = []

            for week, data in reversed(sorted_weeks[:12]):
                chart_weeks.append(week)
                chart_counts.append(data['count'])
                chart_sizes.append(data.get('size_gb', 0))

            html += f'''
        <title>S3 Storage Statistics</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .nav a:hover {{ background: #3a3a3a; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .chart-container {{ max-width: 1400px; margin: 0 auto 3rem auto; background: #2a2a2a; padding: 1.5rem; border-radius: 8px; }}
            .chart-title {{ font-size: 1.2rem; margin-bottom: 1rem; color: #aaa; text-align: center; }}
            canvas {{ max-height: 400px; }}
            .stats-summary {{ max-width: 1400px; margin: 0 auto 2rem auto; padding: 1rem; background: #2a2a2a; border-radius: 8px; }}
            .stats-summary h2 {{ margin-top: 0; color: #aaa; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
            .stat-box {{ background: #1a1a1a; padding: 1rem; border-radius: 6px; text-align: center; }}
            .stat-value {{ font-size: 2rem; font-weight: bold; color: #4a9eff; }}
            .stat-label {{ color: #888; margin-top: 0.5rem; }}
            .weekly-table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            .weekly-table th, .weekly-table td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid #3a3a3a; }}
            .weekly-table th {{ color: #aaa; background: #1a1a1a; }}
            .weekly-table td {{ font-family: monospace; }}
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="gallery">Gallery</a>
            <a href="videos">Videos</a>
            <a href="stats">Capture Stats</a>
        </div>
        <h1>S3 Storage Statistics</h1>

        <div class="stats-summary">
            <h2>Total Storage</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{total_files:,}</div>
                    <div class="stat-label">Total Files</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{total_size_gb:.2f} GB</div>
                    <div class="stat-label">Total Size</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${total_monthly:.3f}</div>
                    <div class="stat-label">Monthly Total</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${yearly_total:.2f}</div>
                    <div class="stat-label">Yearly Total</div>
                </div>
            </div>
            <div style="margin-top: 1rem; color: #666; font-size: 0.85rem;">
                Breakdown: Storage ${storage_cost:.4f} + PUT requests ${put_cost:.4f} + GET requests ${get_cost:.4f}
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">Files per Week</div>
            <canvas id="countChart"></canvas>
        </div>

        <div class="chart-container">
            <div class="chart-title">Storage Size per Week (GB)</div>
            <canvas id="sizeChart"></canvas>
        </div>

        <div class="stats-summary">
            <h2>Weekly Breakdown</h2>
            <table class="weekly-table">
                <thead>
                    <tr>
                        <th>Week</th>
                        <th>Files</th>
                        <th>Size</th>
                        <th>Weekly Cost</th>
                    </tr>
                </thead>
                <tbody>
        '''

            for week, data in sorted_weeks:
                size_gb = data.get('size_gb', 0)
                size_bytes = data.get('size', 0)
                size_mb = size_bytes / 1048576 if size_bytes else size_gb * 1024
                weekly_cost = data.get('weekly_cost_usd', 0)
                size_display = f"{size_mb:.1f} MB" if size_gb < 1 else f"{size_gb:.2f} GB"
                html += f'''
                    <tr>
                        <td>{week}</td>
                        <td>{data['count']:,}</td>
                        <td>{size_display}</td>
                        <td>${weekly_cost:.4f}</td>
                    </tr>
                '''

            html += f'''
                </tbody>
            </table>
            <p style="color: #666; font-size: 0.85rem; margin-top: 1rem;">Last updated: {generated_at}</p>
        </div>

        <script>
        const chartWeeks = {json.dumps(chart_weeks)};
        const chartCounts = {json.dumps(chart_counts)};
        const chartSizes = {json.dumps(chart_sizes)};

        const chartOptions = {{
            responsive: true,
            maintainAspectRatio: true,
            scales: {{
                x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#333' }} }},
                y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#333' }} }}
            }},
            plugins: {{ legend: {{ labels: {{ color: '#aaa' }} }} }}
        }};

        new Chart(document.getElementById('countChart'), {{
            type: 'bar',
            data: {{
                labels: chartWeeks,
                datasets: [{{
                    label: 'Files',
                    data: chartCounts,
                    backgroundColor: '#4a9eff'
                }}]
            }},
            options: chartOptions
        }});

        new Chart(document.getElementById('sizeChart'), {{
            type: 'bar',
            data: {{
                labels: chartWeeks,
                datasets: [{{
                    label: 'Size (GB)',
                    data: chartSizes,
                    backgroundColor: '#10b981'
                }}]
            }},
            options: chartOptions
        }});
        </script>
            '''
        else:
            # Cache not available - show error
            html += f'''
            <title>S3 Storage Statistics</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ text-align: center; margin-bottom: 1.5rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
                .error {{ max-width: 800px; margin: 2rem auto; padding: 2rem; background: #2a2a2a; border-radius: 8px; text-align: center; }}
                .error h1 {{ color: #ef4444; }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a>
                <a href="../gardencam">Latest</a>
            </div>
            <div class="error">
                <h1>Cache Not Available</h1>
                <p>The storage summary cache has not been generated yet.</p>
                <p style="color: #888;">Error: {cache_error}</p>
                <p style="color: #666; font-size: 0.9rem;">The cache is updated hourly by a scheduled Lambda function.</p>
            </div>
            '''

    elif path.startswith(f'/{stage}/gardencam/timelapse/schedule') or path.startswith('/gardencam/timelapse/schedule'):
        # Timelapse schedule page
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        html += '''
        <meta charset="UTF-8">
        <title>Timelapse Schedule - Garden Camera</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }
            .nav { text-align: center; margin-bottom: 1.5rem; }
            .nav a { color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }
            .nav a:hover { background: #3a3a3a; }
            h1 { text-align: center; margin-bottom: 2rem; }
            .container { max-width: 1200px; margin: 0 auto; }
            .schedule-section { background: #2a2a2a; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }
            .schedule-section h2 { margin-top: 0; color: #4a9eff; }
            .schedule-item { background: #1a1a1a; padding: 1rem; margin: 1rem 0; border-radius: 6px; border-left: 4px solid #4a9eff; }
            .schedule-item h3 { margin: 0 0 0.5rem 0; color: #fff; }
            .schedule-item p { margin: 0.25rem 0; color: #aaa; }
            .status { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.85rem; margin-left: 0.5rem; }
            .status.active { background: #10b981; color: #fff; }
            .status.dryrun { background: #f59e0b; color: #000; }
            table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
            th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #3a3a3a; }
            th { color: #4a9eff; background: #1a1a1a; }
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="timelapse">Timelapse Index</a>
            <a href="timelapse/videos">All Videos</a>
        </div>
        <div class="container">
            <h1>Timelapse Automation Schedule</h1>

            <div class="schedule-section">
                <h2>Video Generation</h2>
                <div class="schedule-item">
                    <h3>Weekly Timelapse Creation <span class="status active">ACTIVE</span></h3>
                    <p><strong>Schedule:</strong> Every Sunday at 2:00 AM UTC</p>
                    <p><strong>Duration:</strong> 20 seconds per video (480 frames at 24fps)</p>
                    <p><strong>Output:</strong> videos/timelapse_YYYYMMDD-YYYYMMDD.mp4</p>
                    <p><strong>Lambda:</strong> gardencam-timelapse-generator (3GB memory, 15 min timeout)</p>
                    <p><strong>Next Run:</strong> Next Sunday 02:00 UTC</p>
                </div>
            </div>

            <div class="schedule-section">
                <h2>Image Culling</h2>
                <div class="schedule-item">
                    <h3>Daily Cleanup Check <span class="status dryrun">DRY-RUN</span></h3>
                    <p><strong>Schedule:</strong> Every day at 12:00 PM UTC</p>
                    <p><strong>Mode:</strong> Dry-run (no actual deletion yet)</p>
                    <p><strong>Protection:</strong> ALL night images preserved forever</p>
                    <p><strong>Retention:</strong> Latest 14 days always kept</p>
                    <p><strong>Lambda:</strong> gardencam-image-culling (512MB memory, 5 min timeout)</p>
                </div>

                <h3 style="margin-top: 2rem;">Retention Policy</h3>
                <table>
                    <tr>
                        <th>Age</th>
                        <th>Day Images</th>
                        <th>Night Images</th>
                    </tr>
                    <tr>
                        <td>0-14 days</td>
                        <td>Keep all</td>
                        <td>Keep all</td>
                    </tr>
                    <tr>
                        <td>15-30 days</td>
                        <td>Keep 1 per day</td>
                        <td>Keep all</td>
                    </tr>
                    <tr>
                        <td>31-90 days</td>
                        <td>Keep 1 per week</td>
                        <td>Keep all</td>
                    </tr>
                    <tr>
                        <td>90+ days</td>
                        <td>Keep 1 per month</td>
                        <td>Keep all</td>
                    </tr>
                </table>
            </div>

            <div class="schedule-section">
                <h2>Storage Summary</h2>
                <div class="schedule-item">
                    <h3>Hourly Storage Stats Update <span class="status active">ACTIVE</span></h3>
                    <p><strong>Schedule:</strong> Every hour</p>
                    <p><strong>Function:</strong> Calculate S3 storage statistics</p>
                    <p><strong>Lambda:</strong> gardencam-storage-summary</p>
                </div>
            </div>

            <div class="schedule-section">
                <h2>System Information</h2>
                <p><strong>Region:</strong> eu-west-1 (Ireland)</p>
                <p><strong>S3 Bucket:</strong> gardencam-berrylands-eu-west-1</p>
                <p><strong>Video Format:</strong> MP4 (H.264, 1920x1080, 24fps)</p>
                <p><strong>Frame Selection:</strong> Evenly distributed from all images in date range</p>
            </div>
        </div>
        '''

    elif path.startswith(f'/{stage}/gardencam/timelapse/videos') or path.startswith('/gardencam/timelapse/videos'):
        # Redirect to /gardencam/videos
        return {
            'statusCode': 302,
            'headers': {
                'Location': f'/{stage}/gardencam/videos'
            }
        }

    elif path.startswith(f'/{stage}/gardencam/timelapse') or path.startswith('/gardencam/timelapse'):
        # Timelapse index page
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Get latest 3 videos
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        videos = []

        try:
            response = s3.list_objects_v2(
                Bucket=GARDENCAM_BUCKET,
                Prefix='videos/timelapse_'
            )

            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.mp4'):
                        video_id = key.replace('videos/', '').replace('.mp4', '')
                        date_part = video_id.replace('timelapse_', '')
                        try:
                            if '-' in date_part:
                                # Weekly format
                                start_date, end_date = date_part.split('-')
                                video_type = 'weekly'
                            else:
                                # Daily format
                                start_date = date_part
                                end_date = date_part
                                video_type = 'daily'

                            start_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                            end_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
                        except:
                            start_formatted = "Unknown"
                            end_formatted = "Unknown"
                            video_type = 'unknown'

                        videos.append({
                            'id': video_id,
                            'key': key,
                            'size_mb': obj['Size'] / 1048576,
                            'start_date': start_formatted,
                            'end_date': end_formatted,
                            'type': video_type
                        })

            videos.sort(key=lambda v: v['id'], reverse=True)
            weekly_videos = [v for v in videos if v['type'] == 'weekly']
            daily_videos = [v for v in videos if v['type'] == 'daily']
            latest_weekly = weekly_videos[:3]
            latest_daily = daily_videos[:3]
            total_videos = len(videos)

        except Exception as e:
            print(f"Error listing videos: {e}")
            latest_videos = []
            total_videos = 0

        html += f'''
        <title>Timelapse Videos - Garden Camera</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .nav a:hover {{ background: #3a3a3a; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .info-section {{ background: #2a2a2a; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }}
            .info-section h2 {{ margin-top: 0; color: #4a9eff; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0; }}
            .stat-box {{ background: #1a1a1a; padding: 1.5rem; border-radius: 6px; text-align: center; }}
            .stat-value {{ font-size: 2.5rem; font-weight: bold; color: #4a9eff; }}
            .stat-label {{ color: #888; margin-top: 0.5rem; }}
            .latest-videos {{ margin-top: 2rem; }}
            .video-list {{ list-style: none; padding: 0; }}
            .video-list li {{ background: #1a1a1a; padding: 1rem; margin: 0.5rem 0; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }}
            .video-list li:hover {{ background: #252525; }}
            .video-title {{ color: #4a9eff; font-weight: bold; }}
            .video-date {{ color: #888; font-size: 0.9rem; }}
            .button {{ display: inline-block; padding: 0.75rem 1.5rem; background: #4a9eff; color: #fff; text-decoration: none; border-radius: 6px; margin: 0.5rem; }}
            .button:hover {{ background: #3a8eef; }}
            .button.secondary {{ background: #2a2a2a; }}
            .button.secondary:hover {{ background: #3a3a3a; }}
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="videos">All Videos</a>
            <a href="timelapse/schedule">Schedule</a>
        </div>
        <div class="container">
            <h1>Garden Timelapse Videos</h1>

            <div class="info-section">
                <h2>Overview</h2>
                <p>Automated timelapse videos created from garden camera images:</p>
                <ul style="color: #aaa; margin: 1rem 0;">
                    <li><strong>Weekly:</strong> 7 days condensed, 24fps, ~5 seconds</li>
                    <li><strong>Daily:</strong> 24 hours, 12fps, all captures shown</li>
                </ul>

                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-value">{total_videos}</div>
                        <div class="stat-label">Total Videos</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{len(weekly_videos)}</div>
                        <div class="stat-label">Weekly</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{len(daily_videos)}</div>
                        <div class="stat-label">Daily</div>
                    </div>
                </div>

                <div style="text-align: center; margin-top: 1.5rem;">
                    <a href="videos" class="button">View All Videos</a>
                    <a href="timelapse/schedule" class="button secondary">View Schedule</a>
                </div>
            </div>

            <div class="info-section latest-videos">
                <h2>Latest Weekly Videos</h2>
                <ul class="video-list">
        '''

        for video in latest_weekly:
            html += f'''
                <li>
                    <div>
                        <div class="video-title">Week of {video['start_date']}</div>
                        <div class="video-date">{video['start_date']} to {video['end_date']} • {video['size_mb']:.1f} MB</div>
                    </div>
                    <a href="video?id={video['id']}" class="button">Watch</a>
                </li>
            '''

        html += '''
                </ul>
            </div>

            <div class="info-section latest-videos">
                <h2>Latest Daily Videos</h2>
                <ul class="video-list">
        '''

        for video in latest_daily:
            html += f'''
                <li>
                    <div>
                        <div class="video-title">{video['start_date']}</div>
                        <div class="video-date">{video['size_mb']:.1f} MB</div>
                    </div>
                    <a href="video?id={video['id']}" class="button">Watch</a>
                </li>
            '''

        html += '''
                </ul>
            </div>
        </div>
        '''

    elif (path.startswith(f'/{stage}/gardencam/video?') or path.startswith('/gardencam/video?') or
          path == f'/{stage}/gardencam/video' or path == '/gardencam/video'):
        # Single timelapse video player page (not /videos)
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Get video ID from query parameters
        query_params = event.get('queryStringParameters') or {}
        video_id = query_params.get('id')

        if not video_id:
            return {
                'statusCode': 400,
                'body': '<html><body><h1>400 Bad Request</h1><p>Missing video ID parameter.</p></body></html>',
                'headers': {'Content-Type': 'text/html'}
            }

        # Get video from S3
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        key = f"videos/{video_id}.mp4"

        try:
            # Check if video exists
            s3.head_object(Bucket=GARDENCAM_BUCKET, Key=key)

            # Parse date range from video ID
            try:
                date_part = video_id.replace('timelapse_', '')
                start_date, end_date = date_part.split('-')
                start_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                end_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
            except:
                start_formatted = "Unknown"
                end_formatted = "Unknown"

            # Get metadata from DynamoDB
            frame_count = 0
            duration = 20
            try:
                dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
                metadata_table = dynamodb.Table('gardencam-video-metadata')
                metadata_response = metadata_table.get_item(Key={'video_id': video_id})

                if 'Item' in metadata_response:
                    item = metadata_response['Item']
                    frame_count = int(float(item.get('frame_count', 0)))
                    duration = int(float(item.get('duration_seconds', 20)))
            except Exception as e:
                print(f"Error getting metadata for {video_id}: {e}")

            # Generate presigned URL
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': GARDENCAM_BUCKET, 'Key': key},
                ExpiresIn=3600
            )

            # Get file size
            obj_info = s3.head_object(Bucket=GARDENCAM_BUCKET, Key=key)
            size_mb = obj_info['ContentLength'] / 1048576

            # Render single video page
            html += f'''
            <meta charset="UTF-8">
            <title>Video: {start_formatted} to {end_formatted} - Garden Camera</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .nav {{ text-align: center; margin-bottom: 1.5rem; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
                .nav a:hover {{ background: #3a3a3a; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .video-container {{ background: #2a2a2a; border-radius: 8px; padding: 2rem; }}
                .video-container video {{ width: 100%; max-width: 1200px; display: block; margin: 0 auto; border-radius: 6px; background: #000; }}
                .video-info {{ margin-top: 2rem; padding: 1.5rem; background: #1a1a1a; border-radius: 6px; }}
                .video-info h2 {{ margin: 0 0 1rem 0; color: #4a9eff; }}
                .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }}
                .info-item {{ padding: 1rem; background: #2a2a2a; border-radius: 6px; }}
                .info-label {{ color: #888; font-size: 0.9rem; margin-bottom: 0.5rem; }}
                .info-value {{ font-size: 1.5rem; font-weight: bold; color: #4a9eff; }}
                .download-btn {{ display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #4a9eff; color: #fff; text-decoration: none; border-radius: 6px; font-size: 1rem; }}
                .download-btn:hover {{ background: #3a8eef; }}
            </style>
            <div class="nav">
                <a href="../../contents">Home</a>
                <a href="../gardencam">Latest</a>
                <a href="timelapse">Timelapse Index</a>
                <a href="videos">All Videos</a>
            </div>
            <div class="container">
                <div class="video-container">
                    <video controls loop autoplay preload="auto">
                        <source src="{presigned_url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div class="video-info">
                        <h2>Week of {start_formatted} to {end_formatted}</h2>
                        <div class="info-grid">
                            <div class="info-item">
                                <div class="info-label">Frames</div>
                                <div class="info-value">{frame_count}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Duration</div>
                                <div class="info-value">{duration}s</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">File Size</div>
                                <div class="info-value">{size_mb:.1f} MB</div>
                            </div>
                        </div>
                        <a href="{presigned_url}" download class="download-btn">Download Video (MP4)</a>
                    </div>
                </div>
            </div>
            '''

        except s3.exceptions.NoSuchKey:
            html += f'''
            <title>Video Not Found - Garden Camera</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .error {{ max-width: 800px; margin: 2rem auto; padding: 2rem; background: #2a2a2a; border-radius: 8px; text-align: center; }}
            </style>
            <div class="error">
                <h1>Video Not Found</h1>
                <p>The requested video "{video_id}" does not exist.</p>
                <p><a href="videos" style="color: #4a9eff;">View all videos</a></p>
            </div>
            '''
        except Exception as e:
            print(f"Error loading video {video_id}: {e}")
            html += f'''
            <title>Error - Garden Camera</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
                .error {{ max-width: 800px; margin: 2rem auto; padding: 2rem; background: #2a2a2a; border-radius: 8px; text-align: center; }}
            </style>
            <div class="error">
                <h1>Error Loading Video</h1>
                <p>An error occurred while loading the video.</p>
                <p><a href="videos" style="color: #4a9eff;">View all videos</a></p>
            </div>
            '''

    elif path.startswith(f'/{stage}/gardencam/videos') or path.startswith('/gardencam/videos'):
        # Timelapse video gallery page with thumbnails
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        # Get timelapse videos from S3
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        videos = []

        try:
            # List videos from S3
            response = s3.list_objects_v2(
                Bucket=GARDENCAM_BUCKET,
                Prefix='videos/timelapse_'
            )

            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.mp4'):
                        # Extract video ID from filename: videos/timelapse_YYYYMMDD-YYYYMMDD.mp4 or videos/timelapse_YYYYMMDD.mp4
                        video_id = key.replace('videos/', '').replace('.mp4', '')

                        # Parse date range from filename
                        try:
                            date_part = video_id.replace('timelapse_', '')
                            if '-' in date_part:
                                # Weekly format: YYYYMMDD-YYYYMMDD
                                start_date, end_date = date_part.split('-')
                                video_type = 'weekly'
                            else:
                                # Daily format: YYYYMMDD
                                start_date = date_part
                                end_date = date_part
                                video_type = 'daily'

                            start_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                            end_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
                        except:
                            start_formatted = "Unknown"
                            end_formatted = "Unknown"
                            video_type = 'unknown'

                        # Get metadata from DynamoDB if available
                        try:
                            dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
                            metadata_table = dynamodb.Table('gardencam-video-metadata')
                            metadata_response = metadata_table.get_item(Key={'video_id': video_id})

                            if 'Item' in metadata_response:
                                item = metadata_response['Item']
                                # Convert Decimal to int
                                frame_count = int(float(item.get('frame_count', 0)))
                                duration = int(float(item.get('duration_seconds', 5)))
                                print(f"Video {video_id}: {frame_count} frames, {duration}s")
                            else:
                                print(f"No metadata found for {video_id}")
                                frame_count = 0
                                duration = 5
                        except Exception as e:
                            print(f"Error getting metadata for {video_id}: {e}")
                            frame_count = 0
                            duration = 5

                        # Generate presigned URL (valid for 1 hour)
                        presigned_url = s3.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': GARDENCAM_BUCKET, 'Key': key},
                            ExpiresIn=3600
                        )

                        videos.append({
                            'id': video_id,
                            'key': key,
                            'url': presigned_url,
                            'size_mb': obj['Size'] / 1048576,
                            'last_modified': obj['LastModified'].isoformat(),
                            'start_date': start_formatted,
                            'end_date': end_formatted,
                            'frame_count': frame_count,
                            'duration': duration,
                            'type': video_type
                        })

            # Sort by video ID (date) descending and separate by type
            videos.sort(key=lambda v: v['id'], reverse=True)
            weekly_videos = [v for v in videos if v['type'] == 'weekly']
            daily_videos = [v for v in videos if v['type'] == 'daily']

        except Exception as e:
            print(f"Error listing videos: {e}")
            videos = []

        # Render HTML with thumbnails
        html += f'''
        <meta charset="UTF-8">
        <title>Timelapse Videos - Garden Camera</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 1rem; background: #1a1a1a; color: #fff; }}
            .nav {{ text-align: center; margin-bottom: 1.5rem; }}
            .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 1rem; padding: 0.5rem 1rem; background: #2a2a2a; border-radius: 6px; display: inline-block; }}
            .nav a:hover {{ background: #3a3a3a; }}
            h1 {{ text-align: center; margin-bottom: 2rem; }}
            .video-grid {{ max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; }}
            .video-card {{ background: #2a2a2a; border-radius: 8px; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; text-decoration: none; display: block; color: inherit; }}
            .video-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 16px rgba(0,0,0,0.3); }}
            .video-thumbnail {{ width: 100%; height: 180px; background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%); display: flex; align-items: center; justify-content: center; position: relative; }}
            .play-icon {{ width: 60px; height: 60px; background: rgba(74, 158, 255, 0.9); border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
            .play-icon::after {{ content: ''; width: 0; height: 0; border-style: solid; border-width: 12px 0 12px 20px; border-color: transparent transparent transparent #fff; margin-left: 4px; }}
            .video-metadata {{ padding: 1rem; }}
            .video-metadata h3 {{ margin: 0 0 0.75rem 0; color: #4a9eff; font-size: 1rem; }}
            .video-metadata p {{ margin: 0.25rem 0; color: #aaa; font-size: 0.85rem; }}
            .video-stats {{ display: flex; justify-content: space-between; margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #3a3a3a; }}
            .stat {{ text-align: center; flex: 1; }}
            .stat-value {{ font-weight: bold; color: #4a9eff; display: block; }}
            .stat-label {{ font-size: 0.75rem; color: #666; }}
            .no-videos {{ max-width: 800px; margin: 2rem auto; padding: 2rem; background: #2a2a2a; border-radius: 8px; text-align: center; }}
        </style>
        <div class="nav">
            <a href="../../contents">Home</a>
            <a href="../gardencam">Latest</a>
            <a href="timelapse">Timelapse Index</a>
            <a href="timelapse/schedule">Schedule</a>
            <a href="gallery">Gallery</a>
            <a href="stats">Capture Stats</a>
        </div>
        <h1>Timelapse Videos</h1>
        '''

        if weekly_videos or daily_videos:
            # Weekly videos section
            if weekly_videos:
                html += f'''
                <div style="max-width: 1400px; margin: 0 auto 3rem auto;">
                    <h2 style="color: #4a9eff; margin-bottom: 1rem; padding-left: 0.5rem;">Weekly Timelapses ({len(weekly_videos)})</h2>
                    <p style="color: #888; margin-bottom: 1.5rem; padding-left: 0.5rem;">7-day timelapses at 24fps, ~5 seconds each</p>
                    <div class="video-grid">
                '''
                for video in weekly_videos:
                    html += f'''
                    <a href="video?id={video['id']}" class="video-card">
                        <div class="video-thumbnail">
                            <div class="play-icon"></div>
                        </div>
                        <div class="video-metadata">
                            <h3>Week of {video['start_date']}</h3>
                            <p>{video['start_date']} to {video['end_date']}</p>
                            <div class="video-stats">
                                <div class="stat">
                                    <span class="stat-value">{video['frame_count']}</span>
                                    <span class="stat-label">frames</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-value">{video['duration']}s</span>
                                    <span class="stat-label">duration</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-value">{video['size_mb']:.1f} MB</span>
                                    <span class="stat-label">size</span>
                                </div>
                            </div>
                        </div>
                    </a>
                    '''
                html += '</div></div>'

            # Daily videos section
            if daily_videos:
                html += f'''
                <div style="max-width: 1400px; margin: 0 auto;">
                    <h2 style="color: #4a9eff; margin-bottom: 1rem; padding-left: 0.5rem;">Daily Timelapses ({len(daily_videos)})</h2>
                    <p style="color: #888; margin-bottom: 1.5rem; padding-left: 0.5rem;">24-hour timelapses at 12fps, showing every capture</p>
                    <div class="video-grid">
                '''
                for video in daily_videos:
                    html += f'''
                    <a href="video?id={video['id']}" class="video-card">
                        <div class="video-thumbnail">
                            <div class="play-icon"></div>
                        </div>
                        <div class="video-metadata">
                            <h3>{video['start_date']}</h3>
                            <div class="video-stats">
                                <div class="stat">
                                    <span class="stat-value">{video['frame_count']}</span>
                                    <span class="stat-label">frames</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-value">{video['duration']}s</span>
                                    <span class="stat-label">duration</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-value">{video['size_mb']:.1f} MB</span>
                                    <span class="stat-label">size</span>
                                </div>
                            </div>
                        </div>
                    </a>
                    '''
                html += '</div></div>'
            html += '</div>'
        else:
            html += '''
            <div class="no-videos">
                <h2>No Videos Yet</h2>
                <p>Timelapse videos are generated weekly on Sundays at 2 AM UTC.</p>
                <p style="color: #666; margin-top: 1rem;">Videos will appear here once the first weekly generation completes.</p>
            </div>
            '''

    elif path == f'/{stage}/gardencam' or path == '/gardencam':
        # Check authentication
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="Garden Camera"'
                }
            }

        images = get_latest_gardencam_images(3)
        if images:
            html += f'''{THEME_CSS_JS}
            <title>Garden Camera</title>
            <style>
                body {{ font-family: var(--font); text-align: center; margin: 1rem; background: var(--bg); color: var(--text); }}
                h1 {{ margin-bottom: 1rem; font-size: 2rem; }}
                .gallery-link {{ display: inline-block; margin-bottom: 1.5rem; padding: 0.5rem 1.5rem; background: var(--card-bg); color: var(--accent); text-decoration: none; border-radius: 8px; border: 1px solid var(--divider); transition: opacity 0.2s; }}
                .gallery-link:hover {{ opacity: 0.8; }}
                .gallery {{ display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; max-width: 1024px; margin: 0 auto; }}
                .image-container {{ flex: 1; min-width: 280px; max-width: 340px; }}
                .image-container a {{ display: block; cursor: pointer; }}
                .image-container img {{ width: 100%; height: auto; border-radius: 8px; transition: opacity 0.2s; }}
                .image-container img:hover {{ opacity: 0.85; }}
                .timestamp {{ color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.9rem; }}
                .label {{ color: var(--text-secondary); font-weight: bold; margin-bottom: 0.5rem; font-size: 1rem; }}

                /* Mobile/Tablet - stack vertically */
                @media (max-width: 1024px) {{
                    body {{ margin: 0.5rem; }}
                    h1 {{ font-size: 1.5rem; margin-bottom: 0.75rem; }}
                    .gallery {{ flex-direction: column; gap: 1rem; }}
                    .image-container {{ min-width: 100%; max-width: 100%; }}
                    .label {{ font-size: 1rem; }}
                    .timestamp {{ font-size: 0.85rem; }}
                }}
            </style>
            <div style="text-align: center; margin-bottom: 1rem;">
                <a href="contents" style="color: var(--accent); text-decoration: none;">Home</a>
            </div>
            <h1>Garden Camera</h1>
            <a href="gardencam/gallery" class="gallery-link">View Full Gallery</a>
            <a href="gardencam/videos" class="gallery-link" style="margin-left: 0.5rem;">🎬 Timelapse Videos</a>
            <a href="gardencam/stats" class="gallery-link" style="margin-left: 0.5rem;">Capture Stats</a>
            <a href="gardencam/s3-stats" class="gallery-link" style="margin-left: 0.5rem;">Storage Stats</a>
            <button id="captureBtn" class="gallery-link" style="margin-left: 0.5rem; cursor: pointer;">📷 Capture Now</button>
            <div id="captureStatus" style="margin-top: 0.5rem; font-size: 0.9rem;"></div>
            <script>
            document.getElementById('captureBtn').addEventListener('click', function() {{
                const btn = this;
                const status = document.getElementById('captureStatus');
                btn.disabled = true;
                btn.textContent = '📷 Capturing...';
                status.textContent = 'Sending capture command...';
                status.style.color = '#4a9eff';

                fetch('gardencam/capture', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        status.textContent = data.message || 'Capture command sent! Image will appear in ~30 seconds.';
                        status.style.color = '#10b981';
                        setTimeout(() => {{
                            btn.disabled = false;
                            btn.textContent = '📷 Capture Now';
                        }}, 3000);
                    }})
                    .catch(error => {{
                        status.textContent = 'Error: ' + error.message;
                        status.style.color = '#ef4444';
                        btn.disabled = false;
                        btn.textContent = '📷 Capture Now';
                    }});
            }});

            // Page load performance tracking
            window.addEventListener('load', function() {{
                // Wait a bit for images to fully load
                setTimeout(function() {{
                    const perfData = window.performance.timing;
                    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
                    const domReadyTime = perfData.domContentLoadedEventEnd - perfData.navigationStart;
                    const serverResponseTime = perfData.responseEnd - perfData.requestStart;

                    // Send timing data to server
                    fetch('gardencam/timing', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            pageLoadTime: pageLoadTime,
                            domReadyTime: domReadyTime,
                            serverResponseTime: serverResponseTime,
                            timestamp: new Date().toISOString(),
                            userAgent: navigator.userAgent
                        }})
                    }}).catch(err => console.log('Timing log failed:', err));
                }}, 500);
            }});
            </script>
            <div class="gallery">
            '''
            labels = ['Latest', 'Previous', 'Earlier']
            for idx, img in enumerate(images):
                label = labels[idx] if idx < len(labels) else f'Image {idx+1}'
                resolution_display = f" • {img['resolution']}" if img.get('resolution') else ""
                stats_display = img.get('stats_display', '')

                # Calculate time delta from previous displayed image (if not first)
                time_delta = ""
                if idx > 0:
                    previous_img = images[idx - 1]
                    time_delta = calculate_time_delta(img['timestamp'], previous_img['timestamp'])
                    if time_delta:
                        time_delta = f"{time_delta} "  # Add space after delta

                html += f'''
                <div class="image-container">
                    <div class="label">{label}</div>
                    <a href="gardencam/display?key={img['key']}">
                        <img src="{img['url']}" alt="{label} capture">
                    </a>
                    <p class="timestamp">{time_delta}{img['timestamp']}{resolution_display}{stats_display}</p>
                </div>
                '''
            html += '</div>'
        else:
            return {
                'statusCode': 502,
                'body': '<html><body style="font-family:sans-serif;padding:2rem"><h1>Garden Camera</h1><p>No images available yet.</p></body></html>',
                'headers': {'Content-Type': 'text/html; charset=utf-8'}
            }

    elif path == f'/{stage}/lambda-stats/data' or path == '/lambda-stats/data':
        # Lambda statistics data endpoint - returns JSON
        # This does all the slow data fetching and returns it as JSON
        all_lambda_metrics = get_all_lambda_metrics(days=30)

        # Calculate aggregated stats
        total_cw_invocations = sum(m['invocations'] for m in all_lambda_metrics.values())
        total_cw_errors = sum(m['errors'] for m in all_lambda_metrics.values())
        total_cw_throttles = sum(m['throttles'] for m in all_lambda_metrics.values())

        # Calculate weighted average duration
        total_duration_weighted = sum(m['avg_duration'] * m['invocations'] for m in all_lambda_metrics.values())
        avg_cw_duration = total_duration_weighted / total_cw_invocations if total_cw_invocations > 0 else 0
        max_cw_duration = max((m['max_duration'] for m in all_lambda_metrics.values()), default=0)

        error_rate = (total_cw_errors / total_cw_invocations * 100) if total_cw_invocations > 0 else 0

        # Free tier usage
        total_gb_seconds = sum(m['gb_seconds'] for m in all_lambda_metrics.values())
        FREE_TIER_REQUESTS = 1_000_000
        FREE_TIER_GB_SECONDS = 400_000
        free_tier = {
            'requests_used': int(total_cw_invocations),
            'requests_limit': FREE_TIER_REQUESTS,
            'requests_pct': round(total_cw_invocations / FREE_TIER_REQUESTS * 100, 3),
            'gb_seconds_used': round(total_gb_seconds, 1),
            'gb_seconds_limit': FREE_TIER_GB_SECONDS,
            'gb_seconds_pct': round(total_gb_seconds / FREE_TIER_GB_SECONDS * 100, 3),
        }

        # Sort functions by invocation count
        sorted_functions = sorted(all_lambda_metrics.items(), key=lambda x: x[1]['invocations'], reverse=True)

        # Load DynamoDB logs for IP/User-Agent and path analysis
        from collections import Counter, defaultdict
        stats = get_lambda_execution_stats()

        ip_data = defaultdict(lambda: {'count': 0, 'paths': Counter(), 'timestamps': [], 'user_agents': Counter()})
        ua_data = Counter()

        for item in stats:
            ip = item.get('ip_address', 'Unknown')
            ua = item.get('user_agent', 'Unknown')
            path_item = item.get('path', 'unknown')
            timestamp = item.get('timestamp', '')

            if ip and ip != 'Unknown':
                ip_data[ip]['count'] += 1
                ip_data[ip]['paths'][path_item] += 1
                ip_data[ip]['user_agents'][ua] += 1
                if timestamp:
                    try:
                        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        ip_data[ip]['timestamps'].append(ts)
                    except:
                        pass

            if ua and ua != 'Unknown':
                ua_data[ua] += 1

        # Get geolocation for top IPs (limit to 10 to avoid rate limits)
        import time as time_module
        top_ips = sorted(ip_data.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
        ip_geo_data = []
        country_counts = Counter()

        for ip, data in top_ips:
            time_module.sleep(0.15)  # Rate limit
            geo = get_ip_geolocation(ip)
            top_path = data['paths'].most_common(1)[0] if data['paths'] else ('unknown', 0)
            top_ua = data['user_agents'].most_common(1)[0] if data['user_agents'] else ('Unknown', 0)

            ip_geo_data.append({
                'ip': ip,
                'count': data['count'],
                'country': geo['country'],
                'city': geo['city'],
                'top_path': top_path[0],
                'top_ua': top_ua[0]
            })
            country_counts[geo['country']] += data['count']

        top_uas = ua_data.most_common(10)

        # Path analysis (DynamoDB only, filter out empty paths from backfill)
        path_counts = Counter(item.get('path') for item in stats if item.get('path'))
        total_requests = sum(path_counts.values())
        top_paths = path_counts.most_common(10)

        # Generate histogram data for last 7 days with 28 buckets (6-hour intervals)
        # Aligned to midnight, 6am, noon, 6pm
        now = datetime.utcnow()

        # Find midnight 7 days ago
        seven_days_ago = now - timedelta(days=7)
        midnight_7_days_ago = seven_days_ago.replace(hour=0, minute=0, second=0, microsecond=0)

        bucket_duration = timedelta(hours=6)  # 6-hour buckets: 0-6, 6-12, 12-18, 18-24

        # Create 28 time buckets aligned to 0, 6, 12, 18 hours
        buckets = []
        for i in range(28):
            bucket_start = midnight_7_days_ago + (i * bucket_duration)
            bucket_end = bucket_start + bucket_duration
            # Calculate days ago from the middle of the bucket
            bucket_mid = bucket_start + (bucket_duration / 2)
            days_ago = (now - bucket_mid).total_seconds() / 86400
            buckets.append({
                'start': bucket_start,
                'end': bucket_end,
                'label': f'{days_ago:.1f}',
                'paths': Counter()
            })

        # Assign items to buckets
        for item in stats:
            timestamp_str = item.get('timestamp', '')
            path = item.get('path', '')
            if not timestamp_str or not path:
                continue

            try:
                ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if ts < midnight_7_days_ago:
                    continue  # Skip items older than 7 days (before midnight)

                # Find the correct bucket
                for bucket in buckets:
                    if bucket['start'] <= ts < bucket['end']:
                        bucket['paths'][path] += 1
                        break
            except:
                continue

        # Get top 10 paths overall for the legend
        recent_path_counts = Counter()
        for bucket in buckets:
            recent_path_counts.update(bucket['paths'])
        top_recent_paths = [path for path, _ in recent_path_counts.most_common(10)]

        # Prepare histogram data
        histogram_data = {
            'labels': [bucket['label'] for bucket in buckets],
            'datasets': []
        }

        # Create a dataset for each top path
        colors = [
            '#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b',
            '#fa709a', '#fee140', '#30cfd0', '#a8edea', '#fed6e3'
        ]

        for i, path in enumerate(top_recent_paths):
            dataset = {
                'label': path if path else '(root)',
                'data': [bucket['paths'].get(path, 0) for bucket in buckets],
                'backgroundColor': colors[i % len(colors)]
            }
            histogram_data['datasets'].append(dataset)

        # Return JSON data
        return {
            'statusCode': 200,
            'body': json.dumps({
                'summary': {
                    'total_invocations': int(total_cw_invocations),
                    'total_errors': int(total_cw_errors),
                    'total_throttles': int(total_cw_throttles),
                    'error_rate': round(error_rate, 2),
                    'avg_duration': round(avg_cw_duration, 0),
                    'max_duration': round(max_cw_duration, 0)
                },
                'free_tier': free_tier,
                'functions': [
                    {
                        'name': func_name,
                        'invocations': int(func_metrics['invocations']),
                        'errors': int(func_metrics['errors']),
                        'error_rate': round(func_metrics['error_rate'], 2),
                        'avg_duration': round(func_metrics['avg_duration'], 0),
                        'max_duration': round(func_metrics['max_duration'], 0),
                        'memory_mb': func_metrics['memory_mb'],
                        'gb_seconds': round(func_metrics['gb_seconds'], 1)
                    }
                    for func_name, func_metrics in sorted_functions
                ],
                'paths': [
                    {
                        'path': path,
                        'count': count,
                        'percentage': round((count / total_requests * 100) if total_requests > 0 else 0, 1)
                    }
                    for path, count in top_paths
                ],
                'ips': ip_geo_data,
                'user_agents': [
                    {'user_agent': ua, 'count': count}
                    for ua, count in top_uas
                ],
                'histogram': histogram_data
            }),
            'headers': {'Content-Type': 'application/json'}
        }

    elif path == f'/{stage}/lambda-stats' or path == '/lambda-stats':
        # Lambda statistics page - returns HTML skeleton that loads data asynchronously

        html += f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <title>Lambda CloudWatch Metrics</title>
        {THEME_CSS_JS}
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            body {{ font-family: var(--font); margin: 2rem; background: var(--bg); color: var(--text); }}
            h1 {{ color: var(--text); }}
            .container {{ max-width: 1200px; margin: 0 auto; background: var(--card-bg); padding: 2rem; border-radius: 8px; border: 1px solid var(--divider); }}
            table {{ width: 100%; border-collapse: collapse; margin: 2rem 0; }}
            th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--divider); color: var(--text); }}
            th {{ background: var(--divider); font-weight: 600; }}
            tr:hover {{ background: rgba(142,142,147,0.1); }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 2rem 0; }}
            .stat-box {{ background: var(--card-bg); padding: 1.5rem; border-radius: 8px; text-align: center; border: 1px solid var(--divider); }}
            .stat-value {{ font-size: 2rem; font-weight: bold; color: var(--accent); }}
            .stat-label {{ margin-top: 0.5rem; color: var(--text-secondary); }}
            .nav {{ text-align: center; margin-bottom: 2rem; }}
            .nav a {{ color: var(--accent); text-decoration: none; padding: 0.5rem 1rem; background: var(--card-bg); border: 1px solid var(--divider); border-radius: 20px; }}
            .loading {{ text-align: center; padding: 2rem; color: var(--accent); }}
            .spinner {{ border: 3px solid var(--divider); border-top: 3px solid var(--accent); border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 1rem auto; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .error {{ background: rgba(255,59,48,0.1); padding: 1rem; border-radius: 4px; color: var(--error); margin: 1rem 0; }}
            .chart-container {{ margin: 2rem 0; padding: 1rem; background: var(--card-bg); border-radius: 8px; border: 1px solid var(--divider); }}
            .free-tier {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin: 2rem 0; }}
            .tier-card {{ background: var(--card-bg); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--divider); }}
            .tier-card h3 {{ margin: 0 0 0.5rem 0; font-size: 1rem; color: var(--text-secondary); }}
            .tier-card .tier-value {{ font-size: 1.5rem; font-weight: bold; color: var(--accent); }}
            .tier-card .tier-detail {{ font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem; }}
            .tier-bar {{ height: 8px; background: var(--divider); border-radius: 4px; margin-top: 0.75rem; overflow: hidden; }}
            .tier-bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s; }}
        </style>
        </head>
        <body>
        <div class="container">
            <div class="nav"><a href="../contents">← Home</a></div>
            <h1>📊 Lambda CloudWatch Metrics (Last 30 Days)</h1>

            <div class="loading">
                <div class="spinner"></div>
                <p>Loading statistics data...</p>
            </div>

            <div id="content" style="display: none;">
                <div class="stats-grid" id="summary-stats"></div>

                <h2>Free Tier Usage (30 Days)</h2>
                <div class="free-tier" id="free-tier"></div>

                <h2>📈 Path Usage - Last 7 Days (28 × 6-hour buckets)</h2>
                <div class="chart-container">
                    <canvas id="histogramChart"></canvas>
                </div>

                <h2>Functions by Invocation Count</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Function Name</th>
                            <th>Memory</th>
                            <th>Invocations</th>
                            <th>Errors</th>
                            <th>Error Rate</th>
                            <th>Avg Duration (ms)</th>
                            <th>Max Duration (ms)</th>
                            <th>GB-seconds</th>
                        </tr>
                    </thead>
                    <tbody id="functions-tbody"></tbody>
                </table>

                <h2>📍 Path Analysis (Top Endpoints)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Path</th>
                            <th>Requests</th>
                            <th>Percentage</th>
                        </tr>
                    </thead>
                    <tbody id="paths-tbody"></tbody>
                </table>

                <h2>🌍 IP Address Analysis with Geolocation</h2>
                <table>
                    <thead>
                        <tr>
                            <th>IP Address</th>
                            <th>Country</th>
                            <th>City</th>
                            <th>Requests</th>
                            <th>Top Path</th>
                            <th>User-Agent</th>
                        </tr>
                    </thead>
                    <tbody id="ips-tbody"></tbody>
                </table>

                <h2>📱 Top User-Agents (Browsers/Devices)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>User-Agent</th>
                            <th>Requests</th>
                        </tr>
                    </thead>
                    <tbody id="uas-tbody"></tbody>
                </table>
            </div>
        </div>

        <script>
        async function loadStats() {{
            try {{
                const response = await fetch('./lambda-stats/data');
                if (!response.ok) throw new Error('Failed to load data');

                const data = await response.json();

                // Populate summary stats
                const summary = data.summary;
                document.getElementById('summary-stats').innerHTML = `
                    <div class="stat-box">
                        <div class="stat-value">${{summary.total_invocations.toLocaleString()}}</div>
                        <div class="stat-label">Total Invocations</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${{summary.total_errors.toLocaleString()}}</div>
                        <div class="stat-label">Errors</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${{summary.total_throttles.toLocaleString()}}</div>
                        <div class="stat-label">Throttles</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${{summary.error_rate.toFixed(2)}}%</div>
                        <div class="stat-label">Error Rate</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${{Math.round(summary.avg_duration)}}ms</div>
                        <div class="stat-label">Avg Duration</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">${{Math.round(summary.max_duration)}}ms</div>
                        <div class="stat-label">Max Duration</div>
                    </div>
                `;

                // Populate free tier usage
                const ft = data.free_tier;
                const reqColor = ft.requests_pct < 50 ? '#30D158' : ft.requests_pct < 80 ? '#FF9500' : '#FF3B30';
                const gbColor = ft.gb_seconds_pct < 50 ? '#30D158' : ft.gb_seconds_pct < 80 ? '#FF9500' : '#FF3B30';
                document.getElementById('free-tier').innerHTML = `
                    <div class="tier-card">
                        <h3>Requests</h3>
                        <div class="tier-value">${{ft.requests_pct}}%</div>
                        <div class="tier-detail">${{ft.requests_used.toLocaleString()}} / ${{ft.requests_limit.toLocaleString()}}</div>
                        <div class="tier-bar"><div class="tier-bar-fill" style="width: ${{Math.min(ft.requests_pct, 100)}}%; background: ${{reqColor}};"></div></div>
                    </div>
                    <div class="tier-card">
                        <h3>Compute (GB-seconds)</h3>
                        <div class="tier-value">${{ft.gb_seconds_pct}}%</div>
                        <div class="tier-detail">${{ft.gb_seconds_used.toLocaleString()}} / ${{ft.gb_seconds_limit.toLocaleString()}}</div>
                        <div class="tier-bar"><div class="tier-bar-fill" style="width: ${{Math.min(ft.gb_seconds_pct, 100)}}%; background: ${{gbColor}};"></div></div>
                    </div>
                `;

                // Create histogram chart
                const ctx = document.getElementById('histogramChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: data.histogram.labels,
                        datasets: data.histogram.datasets
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: true,
                        aspectRatio: 3,
                        scales: {{
                            x: {{
                                stacked: true,
                                title: {{
                                    display: true,
                                    text: 'Days Ago'
                                }},
                                ticks: {{
                                    maxRotation: 0,
                                    minRotation: 0,
                                    font: {{ size: 10 }}
                                }}
                            }},
                            y: {{
                                stacked: true,
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Requests'
                                }}
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{ boxWidth: 15, font: {{ size: 11 }} }}
                            }},
                            title: {{
                                display: true,
                                text: 'Request Volume by Path (Stacked)',
                                font: {{ size: 14 }}
                            }}
                        }}
                    }}
                }});

                // Populate functions table
                document.getElementById('functions-tbody').innerHTML = data.functions.map(f => `
                    <tr>
                        <td><strong>${{f.name}}</strong></td>
                        <td>${{f.memory_mb}} MB</td>
                        <td>${{f.invocations.toLocaleString()}}</td>
                        <td>${{f.errors.toLocaleString()}}</td>
                        <td>${{f.error_rate.toFixed(2)}}%</td>
                        <td>${{Math.round(f.avg_duration)}}</td>
                        <td>${{Math.round(f.max_duration)}}</td>
                        <td>${{f.gb_seconds.toFixed(1)}}</td>
                    </tr>
                `).join('');

                // Populate paths table
                document.getElementById('paths-tbody').innerHTML = data.paths.map(p => `
                    <tr>
                        <td><code>${{p.path}}</code></td>
                        <td>${{p.count.toLocaleString()}}</td>
                        <td>${{p.percentage.toFixed(1)}}%</td>
                    </tr>
                `).join('');

                // Populate IPs table
                document.getElementById('ips-tbody').innerHTML = data.ips.map(ip => {{
                    const ua = ip.top_ua.length > 80 ? ip.top_ua.substring(0, 80) + '...' : ip.top_ua;
                    return `
                        <tr>
                            <td><code>${{ip.ip}}</code></td>
                            <td>${{ip.country}}</td>
                            <td>${{ip.city}}</td>
                            <td>${{ip.count.toLocaleString()}}</td>
                            <td><code>${{ip.top_path || '(root)'}}</code></td>
                            <td style="font-size: 0.85rem;">${{ua}}</td>
                        </tr>
                    `;
                }}).join('');

                // Populate user agents table
                document.getElementById('uas-tbody').innerHTML = data.user_agents.map(ua => {{
                    const uaDisplay = ua.user_agent.length > 120 ? ua.user_agent.substring(0, 120) + '...' : ua.user_agent;
                    return `
                        <tr>
                            <td style="font-size: 0.9rem; word-break: break-all;">${{uaDisplay}}</td>
                            <td>${{ua.count.toLocaleString()}}</td>
                        </tr>
                    `;
                }}).join('');

                // Hide loading, show content
                document.querySelector('.loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';
            }} catch (error) {{
                document.querySelector('.loading').innerHTML = `
                    <div class="error">
                        <strong>Error loading statistics:</strong><br>
                        ${{error.message}}
                    </div>
                `;
            }}
        }}

        // Load data when page loads
        loadStats();
        </script>
        </body>
        </html>
        '''

    elif path.startswith(f'/{stage}/memspeed/upload') or path.startswith('/memspeed/upload'):
        # Memspeed upload endpoint
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'WWW-Authenticate': 'Basic realm="memspeed"'
                }
            }

        try:
            body = event.get('body', '{}')
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(body).decode('utf-8')
            data = json.loads(body)
            success, result = save_memspeed_result(data)
            if success:
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Upload successful', 'key': result}),
                    'headers': {'Content-Type': 'application/json'}
                }
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': result}),
                    'headers': {'Content-Type': 'application/json'}
                }
        except json.JSONDecodeError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid JSON: {str(e)}'}),
                'headers': {'Content-Type': 'application/json'}
            }

    elif path.startswith(f'/{stage}/memspeed/download') or path.startswith('/memspeed/download'):
        # Memspeed download endpoint - redirect to presigned URL
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'WWW-Authenticate': 'Basic realm="memspeed"'
                }
            }

        query_params = event.get('queryStringParameters', {}) or {}
        filename = query_params.get('file', '')
        if not filename:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing file parameter'}),
                'headers': {'Content-Type': 'application/json'}
            }

        key = f"{MEMSPEED_DOWNLOADS_PREFIX}{filename}"
        url = get_memspeed_download_url(key)
        if url:
            return {
                'statusCode': 302,
                'body': '',
                'headers': {'Location': url}
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'File not found'}),
                'headers': {'Content-Type': 'application/json'}
            }

    elif path.startswith(f'/{stage}/memspeed/data') or path.startswith('/memspeed/data'):
        # Memspeed JSON API
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'WWW-Authenticate': 'Basic realm="memspeed"'
                }
            }

        results = get_memspeed_results()
        # Remove internal _key field
        for r in results:
            r.pop('_key', None)

        return {
            'statusCode': 200,
            'body': json.dumps({'results': results}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

    elif path == f'/{stage}/memspeed' or path == '/memspeed':
        # Memspeed main page
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1><p>Access denied.</p></body></html>',
                'headers': {
                    'Content-Type': 'text/html',
                    'WWW-Authenticate': 'Basic realm="memspeed"'
                }
            }

        results = get_memspeed_results()
        downloads = get_memspeed_downloads()
        html += render_memspeed_page(results, downloads)

    elif path == f'/{stage}/rcr' or path == '/rcr':
        # Redirect to RCR Lambda function URL
        return {
            'statusCode': 302,
            'headers': {'Location': 'https://k7jrsyq5zi2jexqbrt27zi4nbi0munoe.lambda-url.eu-west-1.on.aws/'},
            'body': ''
        }

    elif path == f'/{stage}/us-vs-the-machines' or path == '/us-vs-the-machines':
        # Redirect to Us vs the Machines Lambda function URL
        return {
            'statusCode': 302,
            'headers': {'Location': 'https://s3fsc6zzxyablo26kgpwcuhh3m0dqphd.lambda-url.eu-west-1.on.aws/'},
            'body': ''
        }

    elif path == f'/{stage}/gotg/manifest.json' or path == '/gotg/manifest.json':
        manifest = json.dumps({
            "name": "Götterdämmerung on the Go",
            "short_name": "GotG",
            "start_url": "/gotg",
            "display": "standalone",
            "background_color": "#000000",
            "theme_color": "#000000",
            "icons": [
                {"src": "https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": "https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": "https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/icon-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
                {"src": "https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
            ]
        })
        return {
            'statusCode': 200,
            'body': manifest,
            'headers': {'Content-Type': 'application/manifest+json'}
        }

    elif path == f'/{stage}/gotg' or path == '/gotg':
        return {
            'statusCode': 200,
            'body': render_gotg_page(),
            'headers': {'Content-Type': 'text/html; charset=utf-8'}
        }

    elif path == f'/{stage}/ai-config' or path == '/ai-config':
        # AI Configuration Matrix
        method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        if method == 'POST':
            body = event.get('body', '')
            if event.get('isBase64Encoded'):
                body = base64.b64decode(body).decode()
            params = dict(p.split('=', 1) for p in body.split('&') if '=' in p)
            app_key = urllib.parse.unquote_plus(params.get('app', ''))
            provider = urllib.parse.unquote_plus(params.get('provider', ''))
            model = urllib.parse.unquote_plus(params.get('model', ''))
            valid_apps = [a['key'] for a in AI_APPS]
            valid_providers = [p['key'] for p in AI_PROVIDERS]
            if app_key in valid_apps and provider in valid_providers:
                set_ai_config(app_key, provider, model)
                configs = get_ai_configs()
                app_name = next(a['name'] for a in AI_APPS if a['key'] == app_key)
                prov_name = next(p['name'] for p in AI_PROVIDERS if p['key'] == provider)
                usage = get_ai_usage()
                return {
                    'statusCode': 200,
                    'body': render_ai_config_page(configs, usage, f"{app_name} switched to {prov_name}"),
                    'headers': {'Content-Type': 'text/html; charset=utf-8'}
                }
        configs = get_ai_configs()
        usage = get_ai_usage()
        return {
            'statusCode': 200,
            'body': render_ai_config_page(configs, usage),
            'headers': {'Content-Type': 'text/html; charset=utf-8'}
        }

    elif path == f'/{stage}/pi-fleet' or path == '/pi-fleet':
        # Pi Fleet Status Dashboard
        pis = get_pi_fleet_status()
        html += render_pi_fleet_page(pis)

    elif path == f'/{stage}/t3' or path == '/t3':
        # Terse Transport Times - K2 bus arrivals
        api_key = TFL_API_KEY

        # Get stop parameter (default to parklands)
        query_params = event.get('queryStringParameters', {}) or {}
        stop = query_params.get('stop', 'parklands').lower()
        if stop not in T3_STOPS:
            stop = 'parklands'

        arrivals, error = t3_fetch_arrivals(api_key, stop)

        # Check if JSON is requested
        headers = event.get('headers', {}) or {}
        accept = headers.get('Accept', headers.get('accept', 'text/html'))

        if 'application/json' in accept:
            # Return JSON for API consumers (e.g., Android app)
            duration_ms = (time.time() - start_time) * 1000
            ip = headers.get('X-Forwarded-For', headers.get('x-forwarded-for', 'Unknown'))
            user_agent = headers.get('User-Agent', headers.get('user-agent', 'Unknown'))
            log_execution_metrics(context, duration_ms, path, ip, user_agent)

            if error:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': error}),
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    }
                }
            return {
                'statusCode': 200,
                'body': t3_format_json(arrivals, stop),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }

        # Return HTML for browsers
        if error:
            return {
                'statusCode': 502,
                'body': f'<html><body style="font-family:sans-serif;padding:2rem"><h1>T3 Error</h1><p>{error}</p></body></html>',
                'headers': {'Content-Type': 'text/html; charset=utf-8'}
            }
        html += t3_format_html(arrivals)

    elif path == f'/{stage}/springcam' or path == '/springcam':
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1></body></html>',
                'headers': {'Content-Type': 'text/html', 'WWW-Authenticate': 'Basic realm="Spring Camera"'}
            }
        images = get_latest_springcam_images(3)
        if images:
            html += f'''{THEME_CSS_JS}
            <title>Spring Camera</title>
            <style>
                body {{ font-family: var(--font); text-align: center; margin: 1rem; background: var(--bg); color: var(--text); }}
                h1 {{ margin-bottom: 1rem; font-size: 2rem; }}
                .gallery-link {{ display: inline-block; margin-bottom: 1.5rem; padding: 0.5rem 1.5rem; background: var(--card-bg); color: var(--accent); text-decoration: none; border-radius: 8px; border: 1px solid var(--divider); transition: opacity 0.2s; }}
                .gallery-link:hover {{ opacity: 0.8; }}
                .gallery {{ display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; max-width: 1024px; margin: 0 auto; }}
                .image-container {{ flex: 1; min-width: 280px; max-width: 340px; }}
                .image-container img {{ width: 100%; height: auto; border-radius: 8px; }}
                .timestamp {{ color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.9rem; }}
                @media (max-width: 1024px) {{
                    .gallery {{ flex-direction: column; }}
                    .image-container {{ min-width: 100%; max-width: 100%; }}
                }}
            </style>
            <div style="text-align: center; margin-bottom: 1rem;">
                <a href="contents" style="color: var(--accent); text-decoration: none;">Home</a>
            </div>
            <h1>Spring Camera</h1>
            <a href="springcam/gallery" class="gallery-link">View Full Gallery</a>
            <div class="gallery">
            '''
            for img in images:
                display_ts = img['timestamp']
                html += f'''
                <div class="image-container">
                    <a href="springcam/fullres?key={img['key']}">
                        <img src="{img['url']}" alt="Spring camera {display_ts}" loading="lazy">
                    </a>
                    <div class="timestamp">{display_ts}</div>
                </div>'''
            html += '</div>'
        else:
            return {
                'statusCode': 502,
                'body': '<html><body style="font-family:sans-serif;padding:2rem"><h1>Spring Camera</h1><p>No images yet.</p></body></html>',
                'headers': {'Content-Type': 'text/html; charset=utf-8'}
            }

    elif path.startswith(f'/{stage}/springcam/gallery') or path.startswith('/springcam/gallery'):
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1></body></html>',
                'headers': {'Content-Type': 'text/html', 'WWW-Authenticate': 'Basic realm="Spring Camera"'}
            }
        all_images = get_all_springcam_images(max_keys=500)
        html += '''
        <title>Spring Camera Gallery</title>
        <style>
            body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; margin: 1rem; }
            h1 { text-align: center; margin-bottom: 1rem; }
            .nav { text-align: center; margin-bottom: 1.5rem; }
            .nav a { color: #4a9eff; text-decoration: none; margin: 0 0.5rem; }
            .gallery { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }
            .thumb { width: 150px; height: 112px; object-fit: cover; border-radius: 4px; cursor: pointer; }
            .thumb:hover { opacity: 0.8; }
            .ts { font-size: 0.7rem; color: #888; text-align: center; margin-top: 2px; }
        </style>
        <h1>Spring Camera Gallery</h1>
        <div class="nav">
            <a href="../contents">Home</a> |
            <a href="../springcam">Latest</a>
        </div>
        <div class="gallery">
        '''
        for img in all_images:
            thumb = springcam_thumb_key(img['key'])
            thumb_url = get_presigned_url(thumb)
            full_url = get_presigned_url(img['key'])
            ts = img['timestamp'][:16] if img['timestamp'] else ''
            html += f'''
            <div>
                <a href="{full_url}" target="_blank">
                    <img class="thumb" src="{thumb_url}" alt="{ts}" loading="lazy">
                </a>
                <div class="ts">{ts}</div>
            </div>'''
        html += '</div>'

    elif path.startswith(f'/{stage}/springcam/fullres') or path.startswith('/springcam/fullres'):
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1></body></html>',
                'headers': {'Content-Type': 'text/html', 'WWW-Authenticate': 'Basic realm="Spring Camera"'}
            }
        params = event.get('queryStringParameters') or {}
        image_key = params.get('key', '')
        if image_key:
            image_url = get_presigned_url(image_key)
            ts = parse_timestamp_from_key(image_key) or image_key
            html += f'''
            <title>Spring Camera - Full Resolution</title>
            <style>
                body {{ background: #000; margin: 0; display: flex; flex-direction: column; align-items: center; }}
                img {{ max-width: 100%; height: auto; }}
                .nav {{ color: #aaa; padding: 0.5rem; font-family: Arial, sans-serif; }}
                .nav a {{ color: #4a9eff; text-decoration: none; margin: 0 0.5rem; }}
            </style>
            <div class="nav"><a href="../../contents">Home</a> | <a href="../springcam">Latest</a> | <a href="gallery">Gallery</a></div>
            <div class="nav">{ts}</div>
            <img src="{image_url}" alt="{ts}">
            '''
        else:
            html += '<p>No image specified.</p>'

    elif path == f'/{stage}/srfcplus' or path == '/srfcplus':
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1></body></html>',
                'headers': {'Content-Type': 'text/html', 'WWW-Authenticate': 'Basic realm="SRFC Plus"'}
            }
        srfc_cookie = get_srfcplus_cookie()
        if not srfc_cookie:
            html = render_srfcplus_setup_page('No session cookie saved yet.')
        else:
            proxied, err = fetch_srfcplus_homepage(srfc_cookie)
            if err == 'expired':
                html = render_srfcplus_setup_page('Session expired — please paste a fresh cookie.')
            elif err:
                html = render_srfcplus_setup_page(f'Could not reach portal: {err}')
            else:
                return {'statusCode': 200, 'body': proxied, 'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path == f'/{stage}/srfcplus/update-cookie' or path == '/srfcplus/update-cookie':
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': '<html><body><h1>401 Unauthorized</h1></body></html>',
                'headers': {'Content-Type': 'text/html', 'WWW-Authenticate': 'Basic realm="SRFC Plus"'}
            }
        if event.get('requestContext', {}).get('http', {}).get('method') == 'POST' or event.get('httpMethod') == 'POST':
            form_body = event.get('body') or ''
            import urllib.parse as _up
            params = dict(_up.parse_qsl(form_body))
            new_cookie = params.get('cookie', '').strip()
            if new_cookie:
                save_srfcplus_cookie(new_cookie)
                return {'statusCode': 302, 'body': '', 'headers': {'Location': '/srfcplus'}}
            html = render_srfcplus_setup_page('No cookie provided — please paste the cookie string.')
        else:
            html = render_srfcplus_setup_page()

    elif path == f'/{stage}/srfcplus/bookings' or path == '/srfcplus/bookings':
        if not check_basic_auth(event, GARDENCAM_PASSWORD):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'}),
                'headers': {'Content-Type': 'application/json', 'WWW-Authenticate': 'Basic realm="SRFC Plus"'}
            }
        srfc_cookie = get_srfcplus_cookie()
        if not srfc_cookie:
            return {'statusCode': 200, 'body': json.dumps({'error': 'No session cookie — visit /srfcplus/update-cookie'}), 'headers': {'Content-Type': 'application/json'}}
        return {
            'statusCode': 200,
            'body': json.dumps(fetch_srfcplus_bookings(srfc_cookie, sport='padel')),
            'headers': {'Content-Type': 'application/json'}
        }

    else:
        html += render_contents_page()

    # If html already has complete structure (DOCTYPE), inject favicon into existing <head>
    if html.strip().startswith('<!DOCTYPE') or html.strip().startswith('<html'):
        if fav and '<head>' in html:
            content = html.replace('<head>', f'<head>{fav}', 1)
        else:
            content = html
    else:
        content = f'<html><head>{fav}{html}</body></html>'

    # Log execution metrics
    duration_ms = (time.time() - start_time) * 1000
    headers = event.get('headers', {}) or {}
    ip = headers.get('X-Forwarded-For', headers.get('x-forwarded-for', 'Unknown'))
    user_agent = headers.get('User-Agent', headers.get('user-agent', 'Unknown'))
    log_execution_metrics(context, duration_ms, path, ip, user_agent)

    return {
        'statusCode': 200,
        'body': content,
        'headers': {
            'Content-Type': 'text/html; charset=utf-8',
        }
    }

if __name__ == "__main__":
    # mock data
    event = {
        'requestContext': {'stage':'-stage-'},
        'headers': {
            'Host':'-host-',
            'X-Forwarded-For':'-ip-',
            'referer': '-referer'
        },
    }
    class Object(object):
        pass
    context = Object()
    context.log_group_name = '-log_group_name-'
    context.log_stream_name = '-log-stream-name-'
    context.aws_request_id = '-request-id-'
    context.function_name = 'mywebsite-local'
    context.memory_limit_in_mb = 128

    # test all the code
    for p in 'event contents cv anything-else'.split():
        event['path'] = f'/-stage-/{p}'
        print(f'{p:<20}', len(pformat(lambda_handler(event, context))))

