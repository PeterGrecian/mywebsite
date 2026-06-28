from pprint import pformat
import os
import base64
import urllib.parse
import urllib.request
from io import BytesIO
from datetime import datetime, timezone, timedelta
import json
import math
import re

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

GARDENCAM_BUCKET = "gardencam-berrylands-eu-west-1"
GARDENCAM_REGION = "eu-west-1"
STARCAM_BUCKET = "starcam-berrylands-eu-west-1"
# Unified astro deliverables (unify-cameras): <camera>/nights/<date>/...
ASTRO_BUCKET = "astro-berrylands-eu-west-1"
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
    """Extract UTC timestamp from filename and convert to Europe/London local time.

    Filenames prior to 2026-04-11 were written in local time; newer ones are UTC.
    We apply BST conversion to all — for old files this double-counts during BST,
    but new files will be correct. Old images scroll off within days.
    """
    try:
        filename_parts = key.replace('.jpg', '').split('_')
        if len(filename_parts) >= 3:
            date_str = filename_parts[1]
            time_str = filename_parts[2]
            utc_dt = datetime(
                int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]),
                int(time_str[:2]), int(time_str[2:4]), int(time_str[4:6]),
                tzinfo=timezone.utc
            )
            try:
                from zoneinfo import ZoneInfo
                local_dt = utc_dt.astimezone(ZoneInfo('Europe/London'))
            except Exception:
                from datetime import timedelta
                year = utc_dt.year
                # Last Sunday in March at 01:00 UTC
                mar31 = datetime(year, 3, 31, 1, tzinfo=timezone.utc)
                bst_start = mar31 - timedelta(days=(mar31.weekday() + 1) % 7)
                # Last Sunday in October at 01:00 UTC
                oct31 = datetime(year, 10, 31, 1, tzinfo=timezone.utc)
                bst_end = oct31 - timedelta(days=(oct31.weekday() + 1) % 7)
                offset = timedelta(hours=1) if bst_start <= utc_dt < bst_end else timedelta(0)
                local_dt = utc_dt + offset
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return None


def get_presigned_url(key, expires_in=3600, bucket=None):
    """Generate presigned URL for a specific S3 key."""
    if not BOTO3_AVAILABLE:
        return None
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket or GARDENCAM_BUCKET, 'Key': key},
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


def get_latest_skycam_images(count=3):
    """Get presigned URLs for the latest N skycam hourly stills.

    Skycam-only — points at the sky, no privacy concern. Keys are of the form
    skycam/YYYY/MM/DD/sky_YYYYMMDD_HHMMSS.jpg. Returns newest first.
    """
    if not BOTO3_AVAILABLE:
        return []
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    objs = []
    for back in range(7):
        d = (datetime.utcnow() - timedelta(days=back))
        prefix = f"skycam/{d.strftime('%Y/%m/%d')}/"
        try:
            resp = s3.list_objects_v2(Bucket=GARDENCAM_BUCKET, Prefix=prefix)
        except Exception:
            continue
        for o in resp.get("Contents", []):
            k = o["Key"]
            name = k.rsplit("/", 1)[-1]
            if name.startswith("sky_") and name.endswith(".jpg") and "_stacked" not in name:
                objs.append(o)
        if len(objs) >= count:
            break
    objs.sort(key=lambda x: x["Key"], reverse=True)
    images = []
    for o in objs[:count]:
        k = o["Key"]
        name = k.rsplit("/", 1)[-1]
        ts_part = name[len("sky_"):-len(".jpg")]
        try:
            ts = datetime.strptime(ts_part, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            ts = o["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
        url = get_presigned_url(k)
        images.append({
            'url': url,
            'full_url': url,
            'timestamp': ts,
            'key': k,
            'resolution': '',
            'stats_display': '',
        })
    return images


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


SKYCAM_PREFIX = "skycam/"
SKYCAM_KEY_PREFIX = "skycam/sky_"


def skycam_thumb_key(key):
    """Convert a skycam image key to its thumbnail key.

    e.g. skycam/sky_20260406_093653.jpg
      -> skycam/thumb_800px_sky_20260406_093653.jpg
    """
    folder, _, basename = key.rpartition('/')
    return f"{folder}/thumb_800px_{basename}"


def get_latest_skycam_images(count=3):
    """Get presigned URLs for the latest N skycam images from S3."""
    if not BOTO3_AVAILABLE:
        return []

    import time
    t0 = time.time()
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    all_objects = []

    # Fast path: try last 60 days by date prefix (both old flat and new date-based paths)
    for days_ago in range(60):
        date = datetime.utcnow() - timedelta(days=days_ago)
        for prefix in [f"skycam/{date.strftime('%Y/%m/%d')}/sky_",
                       f"skycam/sky_{date.strftime('%Y%m%d')}"]:
            try:
                response = s3.list_objects_v2(Bucket=GARDENCAM_BUCKET, Prefix=prefix, MaxKeys=100)
                if "Contents" in response:
                    all_objects.extend(response["Contents"])
            except Exception:
                pass
        if len(all_objects) >= count * 2:
            break

    # Fall back to full scan if fast path found nothing
    if not all_objects:
        for pfx in [SKYCAM_KEY_PREFIX, "skycam/20"]:
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=pfx):
                if "Contents" in page:
                    all_objects.extend(page["Contents"])

    if not all_objects:
        return []

    objects = sorted(
        [o for o in all_objects if o["Key"].endswith('.jpg')],
        key=lambda x: x["LastModified"], reverse=True
    )

    images = []
    for obj in objects[:count * 4]:
        key = obj["Key"]
        thumb_key = skycam_thumb_key(key)
        # Use thumbnail if it exists, otherwise fall back to full image
        try:
            s3.head_object(Bucket=GARDENCAM_BUCKET, Key=thumb_key)
            thumb_url = get_presigned_url(thumb_key)
        except Exception:
            thumb_url = get_presigned_url(key)
        timestamp = parse_timestamp_from_key(key) or obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
        images.append({
            'url': thumb_url,
            'full_url': get_presigned_url(key),
            'timestamp': timestamp,
            'key': key,
        })
        if len(images) >= count:
            break

    print(f"[TIMING] get_latest_skycam_images: {(time.time()-t0)*1000:.0f}ms, {len(images)} images")
    return images


_skycam_images_cache = None
_skycam_images_cache_time = 0
_SKYCAM_CACHE_TTL = 600  # 10 minutes

def get_all_skycam_images(max_keys=None):
    """Get all skycam images from S3, newest first. Cached for 10 minutes."""
    import time
    global _skycam_images_cache, _skycam_images_cache_time
    if not BOTO3_AVAILABLE:
        return []

    now = time.time()
    if _skycam_images_cache is not None and (now - _skycam_images_cache_time) < _SKYCAM_CACHE_TTL:
        images = _skycam_images_cache
    else:
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        paginator = s3.get_paginator('list_objects_v2')
        all_objects = []
        # Search both old flat path and new date-based path
        for pfx in [SKYCAM_KEY_PREFIX, "skycam/20"]:
            for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=pfx):
                if "Contents" in page:
                    all_objects.extend(page["Contents"])

        objects = sorted(
            [o for o in all_objects if o["Key"].endswith('.jpg')],
            key=lambda x: x["LastModified"], reverse=True
        )
        images = []
        for obj in objects:
            key = obj["Key"]
            timestamp = parse_timestamp_from_key(key) or obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
            images.append({'key': key, 'timestamp': timestamp, 'last_modified': obj["LastModified"]})

        _skycam_images_cache = images
        _skycam_images_cache_time = now

    if max_keys:
        return images[:max_keys]
    return images


SPRINGCAM_EARLIEST_DATE = "2026-03-04"  # First springcam image

SKYCAM_EARLIEST_DATE = "2026-04-06"  # First skycam image


def get_springcam_images_for_date(date_str):
    """Get springcam images for a specific date (YYYY-MM-DD), newest first."""
    if not BOTO3_AVAILABLE:
        return []
    prefix = f"springcam/spring_{date_str.replace('-', '')}"
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    try:
        images = []
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if not key.endswith('.jpg'):
                    continue
                timestamp = parse_timestamp_from_key(key) or obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                images.append({'key': key, 'timestamp': timestamp})
        images.sort(key=lambda x: x['timestamp'], reverse=True)
        return images
    except Exception as e:
        print(f"Error fetching springcam images for {date_str}: {e}")
        return []


# ── Starcam ──────────────────────────────────────────────────────────────────

STARCAM_PREFIX = "frames/"
STARCAM_KEY_PREFIX = "frames/star_"
STARCAM_EARLIEST_DATE = "2026-05-17"  # First starcam image


def starcam_thumb_key(key):
    """Convert a starcam image key to its 800px thumbnail key.

    e.g. frames/star_20260517_111057_stacked.jpg
      -> frames/thumb_800px_star_20260517_111057_stacked.jpg
    """
    folder, _, basename = key.rpartition('/')
    return f"{folder}/thumb_800px_{basename}"


def get_latest_starcam_images(count=3):
    """Get presigned URLs for the latest N starcam images from S3."""
    if not BOTO3_AVAILABLE:
        return []

    import time
    t0 = time.time()
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    all_objects = []

    # Fast path: try last 60 days by date prefix
    for days_ago in range(60):
        date = datetime.utcnow() - timedelta(days=days_ago)
        prefix = f"frames/star_{date.strftime('%Y%m%d')}"
        try:
            response = s3.list_objects_v2(Bucket=STARCAM_BUCKET, Prefix=prefix, MaxKeys=100)
            if "Contents" in response:
                all_objects.extend(response["Contents"])
            if len(all_objects) >= count * 2:
                break
        except Exception:
            pass

    # Fall back to full scan if fast path found nothing
    if not all_objects:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=STARCAM_BUCKET, Prefix=STARCAM_KEY_PREFIX):
            if "Contents" in page:
                all_objects.extend(page["Contents"])

    if not all_objects:
        return []

    objects = sorted(
        [o for o in all_objects if o["Key"].endswith('.jpg')],
        key=lambda x: x["Key"], reverse=True
    )

    images = []
    for obj in objects[:count * 4]:
        key = obj["Key"]
        thumb_key = starcam_thumb_key(key)
        timestamp = parse_timestamp_from_key(key) or obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
        images.append({
            'url': get_presigned_url(thumb_key, bucket=STARCAM_BUCKET),
            'full_url': get_presigned_url(key, bucket=STARCAM_BUCKET),
            'timestamp': timestamp,
            'key': key,
        })
        if len(images) >= count:
            break

    print(f"[TIMING] get_latest_starcam_images: {(time.time()-t0)*1000:.0f}ms, {len(images)} images")
    return images


def get_all_starcam_images(max_keys=None):
    """Get all starcam images from S3, newest first."""
    if not BOTO3_AVAILABLE:
        return []
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    paginator = s3.get_paginator('list_objects_v2')
    all_objects = []
    for page in paginator.paginate(Bucket=STARCAM_BUCKET, Prefix=STARCAM_KEY_PREFIX):
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


def get_starcam_images_for_date(date_str):
    """Get starcam images for a specific date (YYYY-MM-DD), newest first."""
    if not BOTO3_AVAILABLE:
        return []
    prefix = f"frames/star_{date_str.replace('-', '')}"
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    try:
        images = []
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=STARCAM_BUCKET, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if not key.endswith('.jpg'):
                    continue
                timestamp = parse_timestamp_from_key(key) or obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                images.append({'key': key, 'timestamp': timestamp})
        images.sort(key=lambda x: x['timestamp'], reverse=True)
        return images
    except Exception as e:
        print(f"Error fetching starcam images for {date_str}: {e}")
        return []


def get_skycam_day_list():
    """Generate list of days with skycam images, newest first. No S3 queries."""
    start = datetime.strptime(SKYCAM_EARLIEST_DATE, '%Y-%m-%d')
    end = datetime.utcnow()
    days = []
    current = end
    while current >= start:
        day_str = current.strftime('%Y-%m-%d')
        day_label = current.strftime('%Y-%m-%d (%A)')
        days.append({'date': day_str, 'label': day_label})
        current -= timedelta(days=1)
    return days


def get_skycam_images_for_date(date_str):
    """Get skycam images for a specific date (YYYY-MM-DD), newest first."""
    if not BOTO3_AVAILABLE:
        return []
    date_compact = date_str.replace('-', '')
    # Search both old flat path and new date-based path
    prefixes = [
        f"skycam/{date_str.replace('-', '/')}/sky_",     # new: skycam/2026/04/19/sky_
        f"skycam/sky_{date_compact}",                     # old: skycam/sky_20260419
    ]
    s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
    try:
        images = []
        paginator = s3.get_paginator('list_objects_v2')
        for prefix in prefixes:
            for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if not key.endswith('.jpg'):
                        continue
                    timestamp = parse_timestamp_from_key(key) or obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                    images.append({'key': key, 'timestamp': timestamp})
        images.sort(key=lambda x: x['timestamp'], reverse=True)
        return images
    except Exception as e:
        print(f"Error fetching skycam images for {date_str}: {e}")
        return []


def _iso_week_for_date(date_str):
    """Return ISO week string like '2026-W16' for a date string 'YYYY-MM-DD'."""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _today_london():
    """Return today's date as YYYY-MM-DD in Europe/London timezone."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo('Europe/London'))
    except ImportError:
        now = datetime.utcnow()
    return now.strftime('%Y-%m-%d')


def _days_in_week(week_iso, earliest_date):
    """Return list of YYYY-MM-DD strings for days in given ISO week, bounded by earliest_date and today."""
    from datetime import date
    iso_year, iso_week = int(week_iso[:4]), int(week_iso.split('W')[1])
    monday = date.fromisocalendar(iso_year, iso_week, 1)
    earliest = date.fromisoformat(earliest_date)
    today = date.fromisoformat(_today_london())
    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        if d < earliest:
            continue
        if d > today:
            break
        days.append(d.isoformat())
    return days


def _days_in_month(month_str, earliest_date):
    """Return list of YYYY-MM-DD strings for days in given month, bounded by earliest_date and today."""
    from datetime import date
    import calendar
    year, month = int(month_str[:4]), int(month_str[5:7])
    earliest = date.fromisoformat(earliest_date)
    today = date.fromisoformat(_today_london())
    _, last_day = calendar.monthrange(year, month)
    days = []
    for d in range(1, last_day + 1):
        day = date(year, month, d)
        if day < earliest:
            continue
        if day > today:
            break
        days.append(day.isoformat())
    return days


def _weeks_in_month(month_str, earliest_date):
    """Return ordered list of ISO week strings that overlap with the given month."""
    days = _days_in_month(month_str, earliest_date)
    seen = []
    for d in days:
        w = _iso_week_for_date(d)
        if w not in seen:
            seen.append(w)
    return seen


def _months_in_year(year_str, earliest_date):
    """Return list of YYYY-MM strings for months in given year with possible content."""
    from datetime import date
    year = int(year_str)
    earliest = date.fromisoformat(earliest_date)
    today = date.fromisoformat(_today_london())
    months = []
    for m in range(1, 13):
        first = date(year, m, 1)
        if first > today:
            break
        import calendar
        _, last_day = calendar.monthrange(year, m)
        last = date(year, m, last_day)
        if last < earliest:
            continue
        months.append(f"{year}-{m:02d}")
    return months


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


def get_skycam_stats_for_date(day_str, thin_minutes=0):
    """Get skycam stats from DynamoDB for a given date (YYYY-MM-DD).
    If thin_minutes > 0, keep at most one point per thin_minutes interval.
    Returns list of dicts with 'timestamp', 'exposure_s', 'avg_brightness'.
    """
    if not BOTO3_AVAILABLE:
        return []
    try:
        from boto3.dynamodb.conditions import Key, Attr
        dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
        table = dynamodb.Table('gardencam-stats')
        items = []
        query_kwargs = {
            'IndexName': 'date-index',
            'KeyConditionExpression': Key('date').eq(day_str),
            'FilterExpression': Attr('camera_name').eq('sky'),
        }
        while True:
            response = table.query(**query_kwargs)
            items.extend(response.get('Items', []))
            if 'LastEvaluatedKey' not in response:
                break
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

        items.sort(key=lambda x: x.get('timestamp', ''))
        result = [
            {
                'timestamp': item.get('timestamp', ''),
                'exposure_s': float(item['exposure_s']) if 'exposure_s' in item else None,
                'avg_brightness': float(item.get('avg_brightness', 0)),
            }
            for item in items
        ]
        if thin_minutes > 0 and result:
            from datetime import datetime as _dt, timedelta
            gap = timedelta(minutes=thin_minutes)
            thinned = [result[0]]
            last = _dt.fromisoformat(result[0]['timestamp'])
            for r in result[1:]:
                try:
                    t = _dt.fromisoformat(r['timestamp'])
                except Exception:
                    continue
                if t - last >= gap:
                    thinned.append(r)
                    last = t
            result = thinned
        return result
    except Exception as e:
        print(f"Error fetching skycam stats for {day_str}: {e}")
        return []


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


def get_astro_storage_data():
    """Fetch (capacity, inventory) for /astro/storage from DynamoDB.

    capacity:  items from astro-host-capacity (one per host x filesystem).
    inventory: items from astro-storage-inventory (one per night x location).
    Both scanned whole — the tables are tiny (handful of hosts, tens of
    nights). Returns ([], []) on any error so the page still renders.
    """
    if not BOTO3_AVAILABLE:
        return [], []

    def _scan(name):
        dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
        table = dynamodb.Table(name)
        resp = table.scan()
        items = resp.get('Items', [])
        while 'LastEvaluatedKey' in resp:
            resp = table.scan(ExclusiveStartKey=resp['LastEvaluatedKey'])
            items.extend(resp.get('Items', []))
        return items

    try:
        capacity = _scan('astro-host-capacity')
    except Exception as e:
        print(f"Error fetching astro-host-capacity: {e}")
        capacity = []
    try:
        inventory = _scan('astro-storage-inventory')
    except Exception as e:
        print(f"Error fetching astro-storage-inventory: {e}")
        inventory = []
    return capacity, inventory


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
    """Render the Pi Fleet dashboard HTML — delegated to routes/pi_fleet.py."""
    from routes.pi_fleet import render_pi_fleet_page as _render
    return _render(
        pis,
        is_pi_online=is_pi_online,
        format_uptime=format_uptime,
        format_age=format_age,
        format_to_sigfigs=format_to_sigfigs,
        theme_css_js=THEME_CSS_JS,
    )


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
    from routes.t3 import t3_format_html as _f
    return _f(arrivals, theme_css_js=THEME_CSS_JS,
              t3_seconds_to_quarter_minutes=t3_seconds_to_quarter_minutes)


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
    from routes.memspeed import render_memspeed_page as _f
    return _f(results, downloads, theme_css_js=THEME_CSS_JS)

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
    from routes.srfcplus_setup import render_srfcplus_setup_page as _f
    return _f(message=message, success=success)

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
    from routes.srfcplus import render_srfcplus_page as _f
    return _f()

def render_contents_page():
    from routes.contents import render_contents_page as _f
    return _f(theme_css_js=THEME_CSS_JS)

def render_gotg_page():
    """Render GOTG page — delegated to routes/gotg.py."""
    from routes.gotg import render_gotg_page as _render
    return _render(theme_css_js=THEME_CSS_JS)


def render_stereo_page(img_param=None, video_param=None, svideo_param=None,
                       place_param=None, videos_param=None, beauty_param=None):
    from routes.stereo import (render_index_page, render_place_page, render_videos_page,
                               render_viewer_page, render_video_viewer_page,
                               render_video_sphere_page, render_beauty_page)
    if svideo_param:
        return render_video_sphere_page(theme_css_js=THEME_CSS_JS, video_file=svideo_param)
    if video_param:
        return render_video_viewer_page(theme_css_js=THEME_CSS_JS, video_file=video_param)
    if img_param:
        return render_viewer_page(theme_css_js=THEME_CSS_JS, img_param=img_param)
    if place_param:
        return render_place_page(theme_css_js=THEME_CSS_JS, place=place_param)
    if videos_param in ("visible", "invisible"):
        return render_videos_page(theme_css_js=THEME_CSS_JS, visibility=videos_param)
    if beauty_param:
        return render_beauty_page(theme_css_js=THEME_CSS_JS)
    return render_index_page(theme_css_js=THEME_CSS_JS)


def render_manim_page():
    """Render Manim animations page — delegated to routes/manim.py."""
    from routes.manim import render_manim_page as _render
    return _render(theme_css_js=THEME_CSS_JS)


def render_site_test_page():
    """Render the site test page — delegated to template."""
    _dir = os.path.join(os.path.dirname(__file__), "templates")
    with open(os.path.join(_dir, "site_test.html")) as f:
        return f.read().format(theme_css_js=THEME_CSS_JS)


AI_APPS = [
    {"key": "alerting", "name": "Alerting", "desc": "Incident analysis"},
    {"key": "rcr", "name": "RCR", "desc": "Album ranking"},
    {"key": "uvtm", "name": "Us vs Machines", "desc": "F1 predictions"},
]
AI_PROVIDERS = [
    {"key": "gemini",     "name": "Gemini",     "models": ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]},
    {"key": "openai",     "name": "OpenAI",     "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini"]},
    {"key": "bedrock",    "name": "Bedrock",    "models": ["anthropic.claude-3-haiku-20240307-v1:0", "anthropic.claude-haiku-4-5-20251001-v1:0", "anthropic.claude-3-7-sonnet-20250219-v1:0"]},
    {"key": "cloudflare", "name": "Cloudflare", "models": ["@cf/meta/llama-3.1-8b-instruct", "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "@cf/google/gemma-3-12b-it"]},
]

# USD per million tokens (input, output)
MODEL_PRICING = {
    "gemini-2.5-pro":                                (1.25, 10.00),
    "gemini-2.5-flash":                              (0.30,  2.50),
    "gemini-2.0-flash":                              (0.10,  0.40),
    "gpt-4o-mini":                                   (0.15,  0.60),
    "gpt-4o":                                        (2.50, 10.00),
    "gpt-4.1-mini":                                  (0.40,  1.60),
    "anthropic.claude-3-haiku-20240307-v1:0":        (0.25,  1.25),
    "anthropic.claude-haiku-4-5-20251001-v1:0":      (0.80,  4.00),
    "anthropic.claude-3-7-sonnet-20250219-v1:0":     (3.00, 15.00),
    "@cf/meta/llama-3.1-8b-instruct":               (0.00,  0.00),
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast":     (0.00,  0.00),
    "@cf/google/gemma-3-12b-it":                    (0.00,  0.00),
}


def _token_cost(model, input_tok, output_tok):
    price = MODEL_PRICING.get(model)
    if not price:
        return 0.0
    return (input_tok * price[0] + output_tok * price[1]) / 1_000_000


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
        return {"calls_today": 0, "calls_1m": 0, "calls_10m": 0,
                "input_tokens_today": 0, "output_tokens_today": 0, "cost_today_usd": 0.0,
                "by_app": {}, "by_provider": {}, "recent": []}

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
                "input_tokens": int(item.get("input_tokens", 0)),
                "output_tokens": int(item.get("output_tokens", 0)),
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

    # Per-provider token totals and cost for today
    by_provider = {}
    for prov in AI_PROVIDERS:
        pk = prov["key"]
        prov_calls = [c for c in calls if c["provider"] == pk]
        in_tok = sum(c["input_tokens"] for c in prov_calls)
        out_tok = sum(c["output_tokens"] for c in prov_calls)
        cost = sum(_token_cost(c["model"], c["input_tokens"], c["output_tokens"]) for c in prov_calls)
        by_provider[pk] = {
            "calls": len(prov_calls),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": cost,
        }

    total_input = sum(c["input_tokens"] for c in calls)
    total_output = sum(c["output_tokens"] for c in calls)
    total_cost = sum(_token_cost(c["model"], c["input_tokens"], c["output_tokens"]) for c in calls)

    return {
        "calls_today": len(calls),
        "calls_1m": sum(1 for c in calls if c["ts"] >= t1m),
        "calls_10m": sum(1 for c in calls if c["ts"] >= t10m),
        "input_tokens_today": total_input,
        "output_tokens_today": total_output,
        "cost_today_usd": total_cost,
        "by_app": by_app,
        "by_provider": by_provider,
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
        except Exception as e:
            print(f"SSM get_ai_config failed for {app['key']}: {e}")
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


def get_failover_chain():
    """Read the global failover chain from SSM. Returns a list of {provider, model} dicts."""
    ssm = boto3.client("ssm", region_name="eu-west-1")
    try:
        resp = ssm.get_parameter(Name="/ai-config/failover-chain")
        return json.loads(resp["Parameter"]["Value"]).get("chain", [])
    except ssm.exceptions.ParameterNotFound:
        return []
    except Exception as e:
        print(f"SSM get_failover_chain failed: {e}")
        return []


def set_failover_chain(chain):
    """Write the global failover chain. chain is a list of {provider, model} dicts."""
    ssm = boto3.client("ssm", region_name="eu-west-1")
    ssm.put_parameter(
        Name="/ai-config/failover-chain",
        Value=json.dumps({"chain": chain}),
        Type="String",
        Overwrite=True,
    )


def compute_provider_health(usage):
    """Per-provider health derived from recent call history.

    Returns {provider_key: {status, last_success, last_error, error_msg, recent_n, recent_failures}}.
    status is one of: ok, degraded, failing, unknown.
    """
    by_provider = {}
    recent = (usage or {}).get("recent", [])
    for prov in AI_PROVIDERS:
        pk = prov["key"]
        prov_calls = [c for c in recent if c["provider"] == pk]
        if not prov_calls:
            by_provider[pk] = {"status": "unknown", "last_success": None,
                               "last_error": None, "error_msg": None,
                               "recent_n": 0, "recent_failures": 0}
            continue
        # recent already sorted newest-first by get_ai_usage
        last_success = next((c for c in prov_calls if not c.get("error")), None)
        last_error = next((c for c in prov_calls if c.get("error")), None)
        sample = prov_calls[:10]
        failures = sum(1 for c in sample if c.get("error"))
        if failures == 0:
            status = "ok"
        elif failures >= len(sample):
            status = "failing"
        else:
            status = "degraded"
        by_provider[pk] = {
            "status": status,
            "last_success": last_success["ts"] if last_success else None,
            "last_error": last_error["ts"] if last_error else None,
            "error_msg": last_error["error"] if last_error else None,
            "recent_n": len(sample),
            "recent_failures": failures,
        }
    return by_provider


def render_ai_config_page(configs, usage=None, message=None, chain=None, health=None):
    from routes.claude_usage import _init_config, render_ai_config_page as _f
    _init_config(AI_APPS, AI_PROVIDERS, MODEL_PRICING)
    return _f(configs, usage=usage, message=message, theme_css_js=THEME_CSS_JS,
              ai_apps=AI_APPS, ai_providers=AI_PROVIDERS,
              chain=chain or [], health=health or {})

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

        from routes.gardencam import render_gardencam_stats
        summary = {
            'total_images': total_images, 'day_count': day_count,
            'night_count': night_count, 'stacking_count': stacking_count,
            'avg_brightness': avg_brightness
        }
        html += render_gardencam_stats(windows, summary)
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

            from routes.gardencam import render_gardencam_fullres
            html += render_gardencam_fullres(timestamp, image_url, stats_display)
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

            from routes.gardencam import render_gardencam_display
            html += render_gardencam_display(timestamp, image_url, image_key, stats_display)
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

            from routes.gardencam import render_gallery_week_index
            html += render_gallery_week_index(weeks)

        elif week_param and not day_param:
            # Show days in the selected week - OPTIMIZED: only load images for this week
            current_week_images = get_images_for_week(week_param)

            if not current_week_images:
                html += '<h1>Week not found</h1><p><a href="gallery">Back to Gallery Index</a></p>'
            else:
                # Group week's images by day
                days = group_images_by_days(current_week_images)

                from routes.gardencam import render_gallery_days
                html += render_gallery_days(week_param, days)

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

                from routes.gardencam import render_gallery_images_header
                html += render_gallery_images_header(day_param, week_param, prev_link, next_link)

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

            from routes.gardencam import render_s3_stats
            summary_data = {
                'total_files': total_files, 'total_size_gb': total_size_gb,
                'total_monthly': total_monthly, 'yearly_total': yearly_total,
                'storage_cost': storage_cost, 'put_cost': put_cost,
                'get_cost': get_cost, 'generated_at': generated_at
            }
            html += render_s3_stats(summary_data, sorted_weeks, chart_weeks, chart_counts, chart_sizes)
        else:
            from routes.gardencam import render_s3_stats_error
            html += render_s3_stats_error(cache_error)

    elif path == f'/{stage}/gardencam' or path == '/gardencam':
        # /gardencam is the legacy URL — 301 redirect to the public /skycam.
        # The page now shows only sky-pointing images, so it no longer needs
        # to be private.
        target = '/skycam' if path == '/gardencam' else f'/{stage}/skycam'
        return {
            'statusCode': 301,
            'body': '',
            'headers': {'Location': target},
        }

    elif path == f'/{stage}/skycam/build-info' or path == '/skycam/build-info':
        from routes.gardencam import _init_theme, render_build_info_page
        _init_theme(THEME_CSS_JS)
        return {'statusCode': 200, 'body': render_build_info_page(),
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path == f'/{stage}/skycam/timelapse' or path == '/skycam/timelapse':
        from routes.gardencam import _init_theme, render_timelapse_index
        _init_theme(THEME_CSS_JS)
        qs = event.get('queryStringParameters') or {}
        focus = qs.get('date')
        return {'statusCode': 200, 'body': render_timelapse_index(focus_date=focus),
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path == f'/{stage}/skycam/timelapse-day' or path == '/skycam/timelapse-day':
        from routes.gardencam import render_timelapse_day_fragment
        qs = event.get('queryStringParameters') or {}
        date = (qs.get('date') or '').strip()
        frag = render_timelapse_day_fragment(date) if date else None
        if frag is None:
            return {'statusCode': 400,
                    'body': '<p>invalid date</p>',
                    'headers': {'Content-Type': 'text/html'}}
        return {'statusCode': 200, 'body': frag,
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path == f'/{stage}/skycam/player-poc' or path == '/skycam/player-poc':
        from routes.gardencam import _init_theme, render_player_poc_landing
        _init_theme(THEME_CSS_JS)
        return {'statusCode': 200, 'body': render_player_poc_landing(),
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path == f'/{stage}/skycam/player' or path == '/skycam/player':
        from routes.gardencam import _init_theme, render_skycam_player
        _init_theme(THEME_CSS_JS)
        qs = event.get('queryStringParameters') or {}
        mvqs = event.get('multiValueQueryStringParameters') or {}
        key = qs.get('key', '')
        src = qs.get('src')
        srcs = mvqs.get('src') if mvqs and len(mvqs.get('src') or []) > 1 else None
        def _f(name):
            v = qs.get(name)
            if v in (None, ''): return None
            try: return float(v)
            except (TypeError, ValueError): return None
        # Parse ?clip=a-b,c-d,... into [(a,b),(c,d),...].
        clip_param = qs.get('clip') or ''
        clips_arg = []
        for piece in clip_param.split(','):
            piece = piece.strip()
            if not piece or '-' not in piece:
                continue
            a, _, b = piece.partition('-')
            try:
                clips_arg.append((float(a), float(b)))
            except ValueError:
                continue
        page = render_skycam_player(key, in_sec=_f('in'), out_sec=_f('out'),
                                    src=src, srcs=srcs,
                                    clips=clips_arg or None)
        if page is None:
            return {'statusCode': 400,
                    'body': '<h1>400</h1><p>Invalid key.</p>',
                    'headers': {'Content-Type': 'text/html'}}
        return {'statusCode': 200, 'body': page,
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path == f'/{stage}/skycam' or path == '/skycam':
        # The page no longer shows the 3-latest-images carousel — the
        # carousel was usually stale (yesterday's frames) and pushed the
        # useful links below the fold. The POC banner (Timelapse videos
        # + Clouds + Advanced player) is dropped too: its three links
        # already live in the main `links` row in render_gardencam_main.
        # The legacy `images`/`image_cards`/`poc_banner_html` args are
        # still passed for API compat with the renderer's signature.
        from routes.gardencam import _init_theme, render_gardencam_main
        _init_theme(THEME_CSS_JS)
        html += render_gardencam_main(images=[], image_cards='',
                                       poc_banner_html='')

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
        from routes.lambda_stats import render_lambda_stats_page
        html += render_lambda_stats_page(theme_css_js=THEME_CSS_JS)

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

    elif path == f'/{stage}/stereo' or path == '/stereo':
        qs = event.get('queryStringParameters', {}) or {}
        return {
            'statusCode': 200,
            'body': render_stereo_page(
                img_param=qs.get('img'),
                video_param=qs.get('video'),
                svideo_param=qs.get('svideo'),
                place_param=qs.get('place'),
                videos_param=qs.get('videos'),
                beauty_param=qs.get('beauty'),
            ),
            'headers': {'Content-Type': 'text/html; charset=utf-8'}
        }

    elif path == f'/{stage}/stereo-nav' or path == '/stereo-nav':
        import json as _j
        from routes.stereo import get_neighbours
        qs = event.get('queryStringParameters', {}) or {}
        img_param = qs.get('img', '')
        return {
            'statusCode': 200,
            'body': _j.dumps(get_neighbours(img_param)),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            }
        }

    elif path == f'/{stage}/manim' or path == '/manim':
        return {
            'statusCode': 200,
            'body': render_manim_page(),
            'headers': {'Content-Type': 'text/html; charset=utf-8'}
        }

    elif path == f'/{stage}/ai-config' or path == '/ai-config':
        # AI Configuration Matrix
        method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod', 'GET')
        message = None
        if method == 'POST':
            body = event.get('body', '')
            if event.get('isBase64Encoded'):
                body = base64.b64decode(body).decode()
            params = dict(p.split('=', 1) for p in body.split('&') if '=' in p)
            action = urllib.parse.unquote_plus(params.get('action', 'set'))
            valid_providers = [p['key'] for p in AI_PROVIDERS]

            if action == 'reorder':
                # Comma-separated provider keys, in the new order
                order = urllib.parse.unquote_plus(params.get('order', ''))
                keys = [k for k in order.split(',') if k in valid_providers]
                if keys:
                    # Preserve the existing model for each provider; default to first model
                    existing = {e['provider']: e for e in get_failover_chain()}
                    new_chain = []
                    for k in keys:
                        if k in existing:
                            new_chain.append(existing[k])
                        else:
                            prov = next(p for p in AI_PROVIDERS if p['key'] == k)
                            new_chain.append({"provider": k, "model": prov["models"][0]})
                    set_failover_chain(new_chain)
                    message = "Failover chain updated"
            else:
                app_key = urllib.parse.unquote_plus(params.get('app', ''))
                provider = urllib.parse.unquote_plus(params.get('provider', ''))
                model = urllib.parse.unquote_plus(params.get('model', ''))
                valid_apps = [a['key'] for a in AI_APPS]
                if app_key in valid_apps and provider in valid_providers:
                    set_ai_config(app_key, provider, model)
                    app_name = next(a['name'] for a in AI_APPS if a['key'] == app_key)
                    prov_name = next(p['name'] for p in AI_PROVIDERS if p['key'] == provider)
                    message = f"{app_name} switched to {prov_name}"

        configs = get_ai_configs()
        usage = get_ai_usage()
        chain = get_failover_chain()
        health = compute_provider_health(usage)
        return {
            'statusCode': 200,
            'body': render_ai_config_page(configs, usage, message, chain, health),
            'headers': {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'no-store',
            }
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
        images = get_latest_springcam_images(3)
        if images:
            from routes.camera import render_camera_latest
            html += render_camera_latest('Spring Camera', images, theme_css_js=THEME_CSS_JS,
                                         gallery_path='springcam/gallery', fullres_path='springcam/fullres',
                                         videos_path='springcam/videos')
        else:
            return {
                'statusCode': 502,
                'body': '<html><body style="font-family:sans-serif;padding:2rem"><h1>Spring Camera</h1><p>No images yet.</p></body></html>',
                'headers': {'Content-Type': 'text/html; charset=utf-8'}
            }

    elif path.startswith(f'/{stage}/springcam/gallery') or path.startswith('/springcam/gallery'):
        query_params = event.get('queryStringParameters', {}) or {}
        day_param = query_params.get('day', '')
        week_param = query_params.get('week', '')
        month_param = query_params.get('month', '')
        year_param = query_params.get('year', '')
        page_param = int(query_params.get('page', '1'))
        per_page = 20

        if year_param:
            # Year view: list months
            months = _months_in_year(year_param, SPRINGCAM_EARLIEST_DATE)
            months_with_counts = []
            for m in reversed(months):
                days = _days_in_month(m, SPRINGCAM_EARLIEST_DATE)
                count = sum(len(get_springcam_images_for_date(d)) for d in days)
                if count > 0:
                    months_with_counts.append((m, count))
            from routes.camera import render_gallery_year
            html += render_gallery_year('Spring Camera', year_param, months_with_counts,
                                        gallery_path='gallery', latest_path='../springcam')

        elif month_param:
            # Month view: weeks with their days
            weeks = _weeks_in_month(month_param, SPRINGCAM_EARLIEST_DATE)
            weeks_with_days = []
            for w in reversed(weeks):
                w_days = _days_in_week(w, SPRINGCAM_EARLIEST_DATE)
                # Filter to only days in this month
                w_days = [d for d in w_days if d[:7] == month_param]
                day_counts = []
                for d in reversed(w_days):
                    count = len(get_springcam_images_for_date(d))
                    if count > 0:
                        day_counts.append((d, count))
                if day_counts:
                    weeks_with_days.append((w, day_counts))
            from routes.camera import render_gallery_month
            html += render_gallery_month('Spring Camera', month_param, weeks_with_days,
                                          gallery_path='gallery', latest_path='../springcam',
                                          year_str=month_param[:4])

        elif week_param:
            # Week view: list days in this week
            w_days = _days_in_week(week_param, SPRINGCAM_EARLIEST_DATE)
            days_with_counts = []
            for d in reversed(w_days):
                count = len(get_springcam_images_for_date(d))
                if count > 0:
                    days_with_counts.append((d, count))
            # Determine month for zoom-out (use the Thursday of the week for ISO month)
            from datetime import date as _date
            iso_year, iso_week = int(week_param[:4]), int(week_param.split('W')[1])
            thursday = _date.fromisocalendar(iso_year, iso_week, 4)
            month_str = thursday.strftime('%Y-%m')
            from routes.camera import render_gallery_week
            html += render_gallery_week('Spring Camera', week_param, days_with_counts,
                                         gallery_path='gallery', latest_path='../springcam',
                                         month_str=month_str)

        else:
            # Day view (default: today)
            if not day_param:
                day_param = _today_london()
            all_day_images = get_springcam_images_for_date(day_param)
            total = len(all_day_images)
            total_pages = max(1, math.ceil(total / per_page))
            page_param = max(1, min(page_param, total_pages))
            page_images = all_day_images[(page_param - 1) * per_page : page_param * per_page]
            week_iso = _iso_week_for_date(day_param)
            from routes.camera import render_gallery_day
            html += render_gallery_day(
                'Spring Camera', day_param, page_images,
                page=page_param, total_pages=total_pages, total_images=total,
                thumb_key_fn=springcam_thumb_key,
                gallery_path='gallery', latest_path='../springcam', fullres_path='../springcam/fullres',
                week_iso=week_iso,
            )

    elif path.startswith(f'/{stage}/springcam/videos') or path.startswith('/springcam/videos'):

        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        videos = []
        try:
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix='springcam/videos/'):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if not key.endswith('.mp4'):
                        continue
                    basename = key.rsplit('/', 1)[-1].replace('.mp4', '')
                    videos.append({
                        'key': key,
                        'url': f"play?key={key}",
                        'size_mb': obj['Size'] / 1048576,
                        'label': basename,
                        'is_daily': False,
                    })
        except Exception as e:
            print(f"Error listing springcam videos: {e}")

        from routes.camera import render_videos_day
        html += render_videos_day('Spring Camera', _today_london(), videos,
                                   latest_path='../springcam', gallery_path='gallery',
                                   videos_path='videos', week_iso=_iso_week_for_date(_today_london()))

    elif path.startswith(f'/{stage}/springcam/play') or path.startswith('/springcam/play'):

        query_params = event.get('queryStringParameters', {}) or {}
        video_key = query_params.get('key', '')
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)

        try:
            s3.head_object(Bucket=GARDENCAM_BUCKET, Key=video_key)
            video_url = s3.generate_presigned_url(
                'get_object', Params={'Bucket': GARDENCAM_BUCKET, 'Key': video_key},
                ExpiresIn=7200)
            basename = video_key.rsplit('/', 1)[-1].replace('.mp4', '')
            from routes.camera import render_skycam_player
            html += render_skycam_player(video_url, basename, hours=[])
        except Exception as e:
            print(f"Error loading springcam video: {e}")
            html += '<p style="color:#888; text-align:center; margin-top:3rem;">Video not found.</p>'

    elif path.startswith(f'/{stage}/springcam/fullres') or path.startswith('/springcam/fullres'):
        params = event.get('queryStringParameters') or {}
        image_key = params.get('key', '')
        if image_key:
            image_url = get_presigned_url(image_key)
            ts = parse_timestamp_from_key(image_key) or image_key
            from routes.camera import render_camera_fullres
            html += render_camera_fullres('Spring Camera', image_url, ts,
                                          latest_path='../springcam', gallery_path='gallery')
        else:
            html += '<p>No image specified.</p>'

    elif path == f'/{stage}/astro' or path == '/astro':
        from routes.astro import render_astro_hub
        return {
            'statusCode': 200,
            'body': render_astro_hub(theme_css_js=THEME_CSS_JS),
            'headers': {'Content-Type': 'text/html; charset=utf-8'}
        }

    elif path == f'/{stage}/astro/storage' or path == '/astro/storage':
        # PUBLIC storage status — capacity bars, data inventory & location,
        # archive-tier state. Reads astro-host-capacity + astro-storage-
        # inventory (backfilled from whereisallthedata.csv). See
        # astro/design/storage-status-and-inventory.md.
        from routes.astro import render_astro_storage
        capacity, inventory = get_astro_storage_data()
        return {
            'statusCode': 200,
            'body': render_astro_storage(theme_css_js=THEME_CSS_JS,
                                         capacity=capacity, inventory=inventory),
            'headers': {'Content-Type': 'text/html; charset=utf-8'}
        }

    elif path == f'/{stage}/astro/starcam' or path == '/astro/starcam':
        return {'statusCode': 302, 'headers': {'Location': '/starcam'}, 'body': ''}

    elif re.search(
            r'/astro/(astrocam|eclipticam(?:-v1|-v3w)?)/night/(\d{4}-\d{2}-\d{2})/player/?$',
            path):
        # PUBLIC — advanced multi-source player for one night's deliverables
        # + experiments. Reuses skycam's render_skycam_player (per project
        # memory astro-website-player: shared player pattern). Lists every
        # mp4 under <camera>/nights/<night>/ and every mp4 under the
        # experiments/ subdir; presigns each; first is what loads, ↑/↓
        # cycles. Frame-step, clip in/out, speed, loop, share-URL.
        m = re.search(
            r'/astro/(astrocam|eclipticam(?:-v1|-v3w)?)/night/(\d{4}-\d{2}-\d{2})/player/?$',
            path)
        camera, night = m.group(1), m.group(2)
        try:
            s3 = boto3.client('s3', region_name=GARDENCAM_REGION)
            listing = s3.list_objects_v2(
                Bucket=ASTRO_BUCKET, Prefix=f'{camera}/nights/{night}/')
            mp4_keys = []
            for item in listing.get('Contents', []) or []:
                k = item['Key']
                if not k.endswith('.mp4'):
                    continue
                mp4_keys.append(k)
            # Order: night-root deliverables first (they're the "story of
            # the night"), then experiments alphabetically.
            mp4_keys.sort(
                key=lambda k: (1 if '/experiments/' in k else 0, k))
            urls = [get_presigned_url(k, bucket=ASTRO_BUCKET)
                    for k in mp4_keys]
            if not urls:
                return {'statusCode': 404,
                        'body': '<p>no mp4s for this night yet</p>',
                        'headers': {'Content-Type': 'text/html'}}
            # The underlying render_skycam_player relies on CSS variables
            # (--bg, --text, --accent, --divider) injected via _init_theme.
            # Without this the HUD text disappears (text colour unset →
            # black on dark overlay) and the timeline bar vanishes
            # (background unset → transparent on white body).
            from routes.gardencam import _init_theme
            from routes.astro import render_astro_player
            _init_theme(THEME_CSS_JS)
            page = render_astro_player(camera=camera, night=night,
                                       sources=urls)
            return {'statusCode': 200, 'body': page,
                    'headers': {'Content-Type': 'text/html; charset=utf-8'}}
        except Exception as e:
            return {'statusCode': 500,
                    'body': f'<p>error: {e}</p>',
                    'headers': {'Content-Type': 'text/html'}}

    elif re.search(r'/astro/(astrocam|eclipticam)(/night/\d{4}-\d{2}-\d{2})?/?$',
                   path):
        # PUBLIC — live nightly deliverables (unify-cameras pipeline).
        # /astro/<cam>                    -> dashboard (latest night)
        # /astro/<cam>/night/YYYY-MM-DD  -> that night
        import json as _json
        m = re.search(
            r'/astro/(astrocam|eclipticam)(?:/night/(\d{4}-\d{2}-\d{2}))?/?$',
            path)
        camera, night = m.group(1), m.group(2)
        is_calendar = night is None  # /astro/<cam> alone -> calendar of nights
        titles = {'astrocam': 'Astro Camera', 'eclipticam': 'Ecliptic Camera'}
        # unify-cameras split: each section is now its own top-level S3
        # camera prefix (eclipticam-v3w / eclipticam-v1) with UN-prefixed
        # filenames (max.jpg, not v3w_max.jpg). astrocam is a single camera.
        # Each entry: (s3_camera_prefix, section_label).
        cam_sections = {
            'astrocam': [('astrocam', None)],
            'eclipticam': [('eclipticam-v3w', 'IMX708 Wide (v3w)'),
                           ('eclipticam-v1', 'OV5647 (v1)')],
        }[camera]
        # The camera whose nights drive the calendar + thumbnails (the
        # night camera for eclipticam).
        primary_cam = cam_sections[0][0]
        try:
            s3 = boto3.client('s3', region_name=GARDENCAM_REGION)
            paginator = s3.get_paginator('list_objects_v2')

            def list_all_nights():
                # Union of nights across all section cameras (v1 may publish
                # nights v3w didn't, and vice versa). This is the O(N) listing
                # the calendar used to do on every request; deferred so the
                # manifest fast path skips it entirely.
                night_set = set()
                for s3_cam, _label in cam_sections:
                    for page_resp in paginator.paginate(
                            Bucket=ASTRO_BUCKET, Prefix=f'{s3_cam}/nights/',
                            Delimiter='/'):
                        for cp in page_resp.get('CommonPrefixes') or []:
                            night_set.add(cp['Prefix'].split('/')[-2])
                return sorted(night_set, reverse=True)

            nights = None  # populated lazily below (manifest path needs none)

            if is_calendar:
                # Fast path: a precomputed manifest at <camera>/index.json
                # (written nightly by astro's build-calendar-index) lets us
                # render the whole calendar from ONE S3 object — no per-night
                # list/get/presign, which used to make this page slower every
                # night. The manifest is keyed by the PUBLIC camera name and
                # already merges the v3w+v1 union for eclipticam. Falls back
                # to the per-night build below if it isn't published yet.
                manifest = None
                try:
                    obj = s3.get_object(Bucket=ASTRO_BUCKET,
                                        Key=f'{camera}/index.json')
                    manifest = _json.loads(obj['Body'].read())
                except Exception:
                    manifest = None

                if manifest is not None:
                    nights_meta = []
                    for entry in manifest.get('nights', []):
                        tk = entry.get('thumb_key')
                        thumb_url = (get_presigned_url(tk, bucket=ASTRO_BUCKET)
                                     if tk else None)
                        nights_meta.append({
                            'night': entry.get('night'),
                            'thumb_url': thumb_url,
                            'summary': {
                                'n_frames': entry.get('n_frames'),
                                'n_stacked': entry.get('n_stacked'),
                                'verdict': entry.get('verdict'),
                            }})
                    nights = [m['night'] for m in nights_meta]

                if manifest is None:
                    nights = list_all_nights()
                    if not nights:
                        from routes.astro import render_astro_stub
                        return {
                            'statusCode': 200,
                            'body': render_astro_stub(
                                theme_css_js=THEME_CSS_JS,
                                title=titles[camera]),
                            'headers': {
                                'Content-Type': 'text/html; charset=utf-8'}}
                    # Slow fallback (pre-manifest): build calendar cards from
                    # the primary (night) camera per night — thumbnail
                    # (thumb.jpg, falling back to max.jpg) + summary.json for
                    # the "X of Y frames stacked" line. Filenames are
                    # un-prefixed post-split.
                    nights_meta = []
                    for n in nights:
                        thumb_url = None
                        summary = None
                        listing_n = s3.list_objects_v2(
                            Bucket=ASTRO_BUCKET,
                            Prefix=f'{primary_cam}/nights/{n}/')
                        names_n = {it['Key'].split('/')[-1]: it['Key']
                                   for it in listing_n.get('Contents', []) or []}
                        # Prefer the colour-sweep mid-frame thumb (a single
                        # 10-min stack from the heart of the dark window).
                        # Fall back to the all-night max for legacy nights
                        # without a sweep.
                        for thumb_key in ('thumb.jpg', 'max.jpg'):
                            if thumb_key in names_n:
                                thumb_url = get_presigned_url(
                                    names_n[thumb_key], bucket=ASTRO_BUCKET)
                                break
                        if 'summary.json' in names_n:
                            try:
                                obj = s3.get_object(
                                    Bucket=ASTRO_BUCKET,
                                    Key=names_n['summary.json'])
                                summary = _json.loads(obj['Body'].read())
                            except Exception:
                                pass
                        nights_meta.append({'night': n, 'thumb_url': thumb_url,
                                            'summary': summary})
                # Multi-night combined brightness curve sits at the
                # primary camera's prefix root (un-prefixed filename),
                # refreshed daily by combined-brightness.
                combined_key = f'{primary_cam}/brightness-combined.png'
                combined_url = None
                try:
                    s3.head_object(Bucket=ASTRO_BUCKET, Key=combined_key)
                    combined_url = get_presigned_url(
                        combined_key, bucket=ASTRO_BUCKET)
                except Exception:
                    pass
                # Accumulated moon net: the reference-night max-stack with
                # every marked moon thread, at the primary camera's prefix
                # root, refreshed daily by moon-overlay. Absent on cameras
                # without a net (e.g. eclipticam-v1) -> stays None.
                moon_net_key = f'{primary_cam}/moon-net.png'
                moon_net_url = None
                try:
                    s3.head_object(Bucket=ASTRO_BUCKET, Key=moon_net_key)
                    moon_net_url = get_presigned_url(
                        moon_net_key, bucket=ASTRO_BUCKET)
                except Exception:
                    pass
                from routes.astro import render_astro_camera_calendar
                return {
                    'statusCode': 200,
                    'body': render_astro_camera_calendar(
                        theme_css_js=THEME_CSS_JS, title=titles[camera],
                        camera=camera, nights_with_meta=nights_meta,
                        combined_brightness_url=combined_url,
                        moon_net_url=moon_net_url),
                    'headers': {'Content-Type': 'text/html; charset=utf-8'}}

            # Nights nav strip (nights[:14]). Prefer the precomputed manifest
            # so a per-night page also skips the O(N) listing; fall back to
            # listing if no manifest is published yet.
            try:
                idx_obj = s3.get_object(Bucket=ASTRO_BUCKET,
                                        Key=f'{camera}/index.json')
                manifest = _json.loads(idx_obj['Body'].read())
                nights = [e.get('night') for e in manifest.get('nights', [])]
            except Exception:
                nights = list_all_nights()

            # One section per camera prefix; each has its own listing with
            # un-prefixed filenames (post unify-cameras split).
            sections = []
            for s3_cam, label in cam_sections:
                listing = s3.list_objects_v2(
                    Bucket=ASTRO_BUCKET,
                    Prefix=f'{s3_cam}/nights/{night}/')
                names = {item['Key'].split('/')[-1]: item['Key']
                         for item in listing.get('Contents', []) or []}
                summary = None
                if 'summary.json' in names:
                    obj = s3.get_object(Bucket=ASTRO_BUCKET,
                                        Key=names['summary.json'])
                    summary = _json.loads(obj['Body'].read())
                urls = {}
                for base in ('sweep-colour.mp4', 'sweep-mono.mp4',
                             'sweep-diff.mp4', 'sweep-detrans.mp4',
                             'sweep-detrans-deep.mp4',
                             'poster-colour.jpg', 'poster-mono.jpg',
                             'poster-diff.jpg', 'poster-detrans.jpg',
                             'poster-detrans-deep.jpg',
                             'derot.jpg', 'max.jpg', 'brightness.png',
                             'thumb.jpg'):
                    if base in names:
                        urls[base] = get_presigned_url(
                            names[base], bucket=ASTRO_BUCKET)
                if summary or urls:
                    sections.append({'label': label,
                                     'summary': summary, 'urls': urls})
        except Exception as e:
            return {'statusCode': 500,
                    'body': f'<p>error: {e}</p>',
                    'headers': {'Content-Type': 'text/html'}}
        from routes.astro import render_astro_camera_page
        return {
            'statusCode': 200,
            'body': render_astro_camera_page(
                theme_css_js=THEME_CSS_JS, title=titles[camera],
                camera=camera, night=night, sections=sections,
                nights=nights, is_dashboard=False),
            'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif (path in (f'/{stage}/starcam', '/starcam',
                   f'/{stage}/starcam/nights', '/starcam/nights',
                   f'/{stage}/starcam/nights/all', '/starcam/nights/all')):
        # PUBLIC — calendar index of published nights.
        # /starcam, /starcam/nights = dashboard (hero + last 3 weeks + 'More')
        # /starcam/nights/all       = full history calendar
        is_dashboard = not path.endswith('/all')
        import json as _json
        try:
            s3 = boto3.client('s3', region_name=GARDENCAM_REGION)
            paginator = s3.get_paginator('list_objects_v2')
            nights = []
            for page_resp in paginator.paginate(
                    Bucket=STARCAM_BUCKET, Prefix='nights/',
                    Delimiter='/'):
                for cp in page_resp.get('CommonPrefixes') or []:
                    night_str = cp['Prefix'].split('/')[-2]
                    try:
                        obj = s3.get_object(
                            Bucket=STARCAM_BUCKET,
                            Key=f'nights/{night_str}/summary.json')
                        s = _json.loads(obj['Body'].read())
                        agg = s.get('aggregate', {}) or {}
                        nights.append({
                            'night': night_str,
                            'verdict': s.get('verdict', 'no-data'),
                            'hours_ok': agg.get('hours_ok', 0),
                            'hours_total': agg.get('hours_total', 0),
                            'pole_spread_px': agg.get('pole_spread_px'),
                        })
                    except Exception:
                        continue
            nights.sort(key=lambda n: n['night'], reverse=True)
            hero_url = None
            hero_night = None
            if is_dashboard:
                # Hero plot lives at the bucket root (not under a date).
                hero_url = get_presigned_url(
                    'nights/brightness.png', bucket=STARCAM_BUCKET)
                hero_night = nights[0]['night'] if nights else None
        except Exception as e:
            return {'statusCode': 500,
                    'body': f'<p>error: {e}</p>',
                    'headers': {'Content-Type': 'text/html'}}
        from routes.camera import render_starcam_nights_index
        kwargs = {}
        if is_dashboard:
            kwargs = {'weeks_limit': 3, 'hero_url': hero_url,
                      'hero_night': hero_night}
        return {'statusCode': 200,
                'body': render_starcam_nights_index(nights, **kwargs),
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif (path.startswith(f'/{stage}/starcam/night/') or
          path.startswith('/starcam/night/')):
        # PUBLIC — no auth. Per-night results page.
        # Path: /starcam/night/YYYY-MM-DD
        import json as _json
        import re as _re
        night_str = path.rstrip('/').rsplit('/', 1)[-1]
        if not _re.fullmatch(r'\d{4}-\d{2}-\d{2}', night_str):
            return {'statusCode': 400,
                    'body': '<p>invalid night</p>',
                    'headers': {'Content-Type': 'text/html'}}
        key_prefix = f'nights/{night_str}/'
        try:
            s3 = boto3.client('s3', region_name=GARDENCAM_REGION)
            obj = s3.get_object(Bucket=STARCAM_BUCKET,
                                Key=f'{key_prefix}summary.json')
            summary = _json.loads(obj['Body'].read())
            # List the night's objects to pick up sum_*.jpg etc.
            listing = s3.list_objects_v2(Bucket=STARCAM_BUCKET,
                                         Prefix=key_prefix)
            urls = {}
            for item in listing.get('Contents', []) or []:
                name = item['Key'].split('/')[-1]
                urls[name] = get_presigned_url(
                    item['Key'], bucket=STARCAM_BUCKET)
        except s3.exceptions.NoSuchKey:
            return {'statusCode': 404,
                    'body': f'<p>no data for {night_str}</p>',
                    'headers': {'Content-Type': 'text/html'}}
        except Exception as e:
            return {'statusCode': 500,
                    'body': f'<p>error: {e}</p>',
                    'headers': {'Content-Type': 'text/html'}}
        from routes.camera import render_starcam_night_results
        return {'statusCode': 200,
                'body': render_starcam_night_results(night_str, summary, urls),
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path.startswith(f'/{stage}/starcam/gallery') or path.startswith('/starcam/gallery'):
        query_params = event.get('queryStringParameters', {}) or {}
        day_param = query_params.get('day', '')
        week_param = query_params.get('week', '')
        month_param = query_params.get('month', '')
        year_param = query_params.get('year', '')
        page_param = int(query_params.get('page', '1'))
        per_page = 20

        if year_param:
            months = _months_in_year(year_param, STARCAM_EARLIEST_DATE)
            months_with_counts = []
            for m in reversed(months):
                days = _days_in_month(m, STARCAM_EARLIEST_DATE)
                count = sum(len(get_starcam_images_for_date(d)) for d in days)
                if count > 0:
                    months_with_counts.append((m, count))
            from routes.camera import render_gallery_year
            html += render_gallery_year('Star Camera', year_param, months_with_counts,
                                        gallery_path='gallery', latest_path='../starcam')

        elif month_param:
            weeks = _weeks_in_month(month_param, STARCAM_EARLIEST_DATE)
            weeks_with_days = []
            for w in reversed(weeks):
                w_days = _days_in_week(w, STARCAM_EARLIEST_DATE)
                w_days = [d for d in w_days if d[:7] == month_param]
                day_counts = []
                for d in reversed(w_days):
                    count = len(get_starcam_images_for_date(d))
                    if count > 0:
                        day_counts.append((d, count))
                if day_counts:
                    weeks_with_days.append((w, day_counts))
            from routes.camera import render_gallery_month
            html += render_gallery_month('Star Camera', month_param, weeks_with_days,
                                          gallery_path='gallery', latest_path='../starcam',
                                          year_str=month_param[:4])

        elif week_param:
            w_days = _days_in_week(week_param, STARCAM_EARLIEST_DATE)
            days_with_counts = []
            for d in reversed(w_days):
                count = len(get_starcam_images_for_date(d))
                if count > 0:
                    days_with_counts.append((d, count))
            from datetime import date as _date
            iso_year, iso_week = int(week_param[:4]), int(week_param.split('W')[1])
            thursday = _date.fromisocalendar(iso_year, iso_week, 4)
            month_str = thursday.strftime('%Y-%m')
            from routes.camera import render_gallery_week
            html += render_gallery_week('Star Camera', week_param, days_with_counts,
                                         gallery_path='gallery', latest_path='../starcam',
                                         month_str=month_str)

        else:
            if not day_param:
                day_param = _today_london()
            all_day_images = get_starcam_images_for_date(day_param)
            total = len(all_day_images)
            total_pages = max(1, math.ceil(total / per_page))
            page_param = max(1, min(page_param, total_pages))
            page_images = all_day_images[(page_param - 1) * per_page : page_param * per_page]
            week_iso = _iso_week_for_date(day_param)
            from routes.camera import render_gallery_day
            html += render_gallery_day(
                'Star Camera', day_param, page_images,
                page=page_param, total_pages=total_pages, total_images=total,
                thumb_key_fn=starcam_thumb_key,
                gallery_path='gallery', latest_path='../starcam', fullres_path='../starcam/fullres',
                week_iso=week_iso,
            )

    elif path == f'/{stage}/starcam/timelapse' or path == '/starcam/timelapse':
        from routes.gardencam import _init_theme, render_timelapse_index
        _init_theme(THEME_CSS_JS)
        qs = event.get('queryStringParameters') or {}
        focus = qs.get('date')
        return {'statusCode': 200,
                'body': render_timelapse_index(focus_date=focus, camera='starcam'),
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path == f'/{stage}/starcam/timelapse-day' or path == '/starcam/timelapse-day':
        from routes.gardencam import render_timelapse_day_fragment
        qs = event.get('queryStringParameters') or {}
        date = (qs.get('date') or '').strip()
        frag = render_timelapse_day_fragment(date, camera='starcam') if date else None
        if frag is None:
            return {'statusCode': 400, 'body': '<p>invalid date</p>',
                    'headers': {'Content-Type': 'text/html'}}
        return {'statusCode': 200, 'body': frag,
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path == f'/{stage}/starcam/player' or path == '/starcam/player':
        from routes.gardencam import _init_theme, render_skycam_player
        _init_theme(THEME_CSS_JS)
        qs = event.get('queryStringParameters') or {}
        mvqs = event.get('multiValueQueryStringParameters') or {}
        key = qs.get('key', '')
        src = qs.get('src')
        srcs = mvqs.get('src') if mvqs and len(mvqs.get('src') or []) > 1 else None
        def _f(name):
            v = qs.get(name)
            if v in (None, ''): return None
            try: return float(v)
            except (TypeError, ValueError): return None
        clip_param = qs.get('clip') or ''
        clips_arg = []
        for piece in clip_param.split(','):
            piece = piece.strip()
            if not piece or '-' not in piece:
                continue
            a, _, b = piece.partition('-')
            try:
                clips_arg.append((float(a), float(b)))
            except ValueError:
                continue
        page = render_skycam_player(key, in_sec=_f('in'), out_sec=_f('out'),
                                    src=src, srcs=srcs,
                                    clips=clips_arg or None)
        if page is None:
            return {'statusCode': 400, 'body': '<h1>400</h1><p>Invalid key.</p>',
                    'headers': {'Content-Type': 'text/html'}}
        return {'statusCode': 200, 'body': page,
                'headers': {'Content-Type': 'text/html; charset=utf-8'}}

    elif path.startswith(f'/{stage}/starcam/videos') or path.startswith('/starcam/videos'):

        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        videos = []
        try:
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=STARCAM_BUCKET, Prefix='videos/'):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if not key.endswith('.mp4'):
                        continue
                    basename = key.rsplit('/', 1)[-1].replace('.mp4', '')
                    videos.append({
                        'key': key,
                        'url': f"play?key={key}",
                        'size_mb': obj['Size'] / 1048576,
                        'label': basename,
                        'is_daily': False,
                    })
        except Exception as e:
            print(f"Error listing starcam videos: {e}")

        from routes.camera import render_videos_day
        html += render_videos_day('Star Camera', _today_london(), videos,
                                   latest_path='../starcam', gallery_path='gallery',
                                   videos_path='videos', week_iso=_iso_week_for_date(_today_london()))

    elif path.startswith(f'/{stage}/starcam/play') or path.startswith('/starcam/play'):

        query_params = event.get('queryStringParameters', {}) or {}
        video_key = query_params.get('key', '')
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)

        try:
            s3.head_object(Bucket=STARCAM_BUCKET, Key=video_key)
            video_url = s3.generate_presigned_url(
                'get_object', Params={'Bucket': STARCAM_BUCKET, 'Key': video_key},
                ExpiresIn=7200)
            basename = video_key.rsplit('/', 1)[-1].replace('.mp4', '')
            from routes.camera import render_skycam_player
            html += render_skycam_player(video_url, basename, hours=[])
        except Exception as e:
            print(f"Error loading starcam video: {e}")
            html += '<p style="color:#888; text-align:center; margin-top:3rem;">Video not found.</p>'

    elif path.startswith(f'/{stage}/starcam/fullres') or path.startswith('/starcam/fullres'):
        params = event.get('queryStringParameters') or {}
        image_key = params.get('key', '')
        if image_key:
            image_url = get_presigned_url(image_key, bucket=STARCAM_BUCKET)
            ts = parse_timestamp_from_key(image_key) or image_key
            from routes.camera import render_camera_fullres
            html += render_camera_fullres('Star Camera', image_url, ts,
                                          latest_path='../starcam', gallery_path='gallery')
        else:
            html += '<p>No image specified.</p>'

    elif path == f'/{stage}/skycam' or path == '/skycam':
        images = get_latest_skycam_images(3)
        if images:
            from routes.camera import render_camera_latest
            html += render_camera_latest('Sky Camera', images, theme_css_js=THEME_CSS_JS,
                                         gallery_path='skycam/gallery', fullres_path='skycam/fullres',
                                         videos_path='skycam/videos', starcam_path='skycam/starcam')
        else:
            return {
                'statusCode': 502,
                'body': '<html><body style="font-family:sans-serif;padding:2rem"><h1>Sky Camera</h1><p>No images yet.</p></body></html>',
                'headers': {'Content-Type': 'text/html; charset=utf-8'}
            }

    elif path.startswith(f'/{stage}/skycam/gallery') or path.startswith('/skycam/gallery'):
        query_params = event.get('queryStringParameters', {}) or {}
        day_param = query_params.get('day', '')
        week_param = query_params.get('week', '')
        month_param = query_params.get('month', '')
        year_param = query_params.get('year', '')
        page_param = int(query_params.get('page', '1'))
        per_page = 20

        if year_param:
            months = _months_in_year(year_param, SKYCAM_EARLIEST_DATE)
            months_with_counts = []
            for m in reversed(months):
                days = _days_in_month(m, SKYCAM_EARLIEST_DATE)
                count = sum(len(get_skycam_images_for_date(d)) for d in days)
                if count > 0:
                    months_with_counts.append((m, count))
            from routes.camera import render_gallery_year
            html += render_gallery_year('Sky Camera', year_param, months_with_counts,
                                        gallery_path='gallery', latest_path='../skycam',
                                        videos_path='videos')

        elif month_param:
            weeks = _weeks_in_month(month_param, SKYCAM_EARLIEST_DATE)
            weeks_with_days = []
            for w in reversed(weeks):
                w_days = _days_in_week(w, SKYCAM_EARLIEST_DATE)
                w_days = [d for d in w_days if d[:7] == month_param]
                day_counts = []
                for d in reversed(w_days):
                    count = len(get_skycam_images_for_date(d))
                    if count > 0:
                        day_counts.append((d, count))
                if day_counts:
                    weeks_with_days.append((w, day_counts))
            from routes.camera import render_gallery_month
            html += render_gallery_month('Sky Camera', month_param, weeks_with_days,
                                          gallery_path='gallery', latest_path='../skycam',
                                          year_str=month_param[:4], videos_path='videos')

        elif week_param:
            w_days = _days_in_week(week_param, SKYCAM_EARLIEST_DATE)
            days_with_counts = []
            for d in reversed(w_days):
                count = len(get_skycam_images_for_date(d))
                if count > 0:
                    days_with_counts.append((d, count))
            from datetime import date as _date
            iso_year, iso_week = int(week_param[:4]), int(week_param.split('W')[1])
            thursday = _date.fromisocalendar(iso_year, iso_week, 4)
            month_str = thursday.strftime('%Y-%m')
            from routes.camera import render_gallery_week
            html += render_gallery_week('Sky Camera', week_param, days_with_counts,
                                         gallery_path='gallery', latest_path='../skycam',
                                         month_str=month_str, videos_path='videos')

        else:
            if not day_param:
                day_param = _today_london()
            all_day_images = get_skycam_images_for_date(day_param)
            total = len(all_day_images)
            total_pages = max(1, math.ceil(total / per_page))
            page_param = max(1, min(page_param, total_pages))
            page_images = all_day_images[(page_param - 1) * per_page : page_param * per_page]
            week_iso = _iso_week_for_date(day_param)
            skycam_stats = get_skycam_stats_for_date(day_param, thin_minutes=10)
            from routes.camera import render_gallery_day
            html += render_gallery_day(
                'Sky Camera', day_param, page_images,
                page=page_param, total_pages=total_pages, total_images=total,
                thumb_key_fn=skycam_thumb_key,
                gallery_path='gallery', latest_path='../skycam', fullres_path='../skycam/fullres',
                week_iso=week_iso, videos_path='videos',
                exposure_data=skycam_stats,
            )

    elif path.startswith(f'/{stage}/skycam/fullres') or path.startswith('/skycam/fullres'):
        params = event.get('queryStringParameters') or {}
        image_key = params.get('key', '')
        if image_key:
            image_url = get_presigned_url(image_key)
            ts = parse_timestamp_from_key(image_key) or image_key
            from routes.camera import render_camera_fullres
            html += render_camera_fullres('Sky Camera', image_url, ts,
                                          latest_path='../skycam', gallery_path='gallery')
        else:
            html += '<p>No image specified.</p>'

    elif path.startswith(f'/{stage}/skycam/videos') or path.startswith('/skycam/videos'):
        query_params = event.get('queryStringParameters', {}) or {}

        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)

        def _presign_vid(key):
            return s3.generate_presigned_url(
                'get_object', Params={'Bucket': GARDENCAM_BUCKET, 'Key': key}, ExpiresIn=3600)

        def _list_videos_for_prefix(prefix):
            """List mp4 videos under an S3 prefix, return sorted newest-first."""
            vids = []
            try:
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=prefix):
                    for obj in page.get('Contents', []):
                        key = obj['Key']
                        if not key.endswith('.mp4'):
                            continue
                        basename = key.rsplit('/', 1)[-1].replace('.mp4', '')
                        ts_part = basename.replace('sky_', '')
                        is_daily = ts_part.endswith('_daily')
                        is_combined = ts_part.endswith('_combined')
                        is_night = ts_part.endswith('_night')
                        is_special = is_daily or is_combined or is_night
                        if is_daily:
                            date_part = ts_part.replace('_daily', '')
                            try:
                                dt = datetime.strptime(date_part, '%Y%m%d')
                            except ValueError:
                                dt = obj['LastModified'].replace(tzinfo=None)
                            label = 'Full Day'
                        elif is_combined:
                            date_part = ts_part.replace('_combined', '')
                            try:
                                dt = datetime.strptime(date_part, '%Y%m%d')
                            except ValueError:
                                dt = obj['LastModified'].replace(tzinfo=None)
                            label = 'Full Day (sky + garden)'
                        elif is_night:
                            date_part = ts_part.replace('_night', '')
                            try:
                                dt = datetime.strptime(date_part, '%Y%m%d')
                            except ValueError:
                                dt = obj['LastModified'].replace(tzinfo=None)
                            label = 'Night Sky'
                        else:
                            try:
                                dt = datetime.strptime(ts_part, '%Y%m%d_%H')
                                label = dt.strftime('%H:00')
                            except ValueError:
                                label = ts_part
                                dt = obj['LastModified'].replace(tzinfo=None)
                        vids.append({
                            'key': key,
                            'url': f"play?key={key}",
                            'size_mb': obj['Size'] / 1048576,
                            'label': label, 'dt': dt,
                            'is_daily': is_special,
                        })
            except Exception as e:
                print(f"Error listing skycam videos ({prefix}): {e}")
            vids.sort(key=lambda v: (not v.get('is_daily'), v['dt']), reverse=True)
            return vids

        def _count_videos_for_day(day_str):
            """Count videos for a specific day via S3 prefix."""
            try:
                day_dt = datetime.strptime(day_str, '%Y-%m-%d')
            except ValueError:
                return 0
            prefix = f"skycam/videos/{day_dt.strftime('%Y/%m/%d')}/"
            count = 0
            try:
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=prefix):
                    count += sum(1 for obj in page.get('Contents', []) if obj['Key'].endswith('.mp4'))
            except Exception:
                pass
            return count

        def _count_videos_for_month(month_str):
            """Count videos for a month."""
            try:
                month_dt = datetime.strptime(month_str + '-01', '%Y-%m-%d')
            except ValueError:
                return 0
            prefix = f"skycam/videos/{month_dt.strftime('%Y/%m')}/"
            count = 0
            try:
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=prefix):
                    count += sum(1 for obj in page.get('Contents', []) if obj['Key'].endswith('.mp4'))
            except Exception:
                pass
            return count

        def _days_with_videos_in_month(month_str):
            """Return list of (day_str, count) for days with videos, newest first."""
            try:
                month_dt = datetime.strptime(month_str + '-01', '%Y-%m-%d')
            except ValueError:
                return []
            prefix = f"skycam/videos/{month_dt.strftime('%Y/%m')}/"
            days_seen = {}
            try:
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=prefix):
                    for obj in page.get('Contents', []):
                        key = obj['Key']
                        if not key.endswith('.mp4'):
                            continue
                        parts = key.split('/')
                        if len(parts) >= 5:
                            day_str = f"{parts[2]}-{parts[3]}-{parts[4]}"
                            days_seen[day_str] = days_seen.get(day_str, 0) + 1
            except Exception as e:
                print(f"Error listing skycam videos for month {month_str}: {e}")
            return sorted(days_seen.items(), reverse=True)

        day_param = query_params.get('day', '')
        week_param = query_params.get('week', '')
        month_param = query_params.get('month', '')
        year_param = query_params.get('year', '')
        # Video earliest date matches skycam images
        VIDEO_EARLIEST = SKYCAM_EARLIEST_DATE

        if year_param:
            months = _months_in_year(year_param, VIDEO_EARLIEST)
            months_with_counts = []
            for m in reversed(months):
                count = _count_videos_for_month(m)
                if count > 0:
                    months_with_counts.append((m, count))
            from routes.camera import render_videos_year
            html += render_videos_year('Sky Camera', year_param, months_with_counts,
                                       latest_path='../skycam', gallery_path='gallery', videos_path='videos')

        elif month_param:
            days_list = _days_with_videos_in_month(month_param)
            from routes.camera import render_videos_month
            html += render_videos_month('Sky Camera', month_param, days_list,
                                         latest_path='../skycam', gallery_path='gallery',
                                         videos_path='videos', year_str=month_param[:4])

        elif week_param:
            w_days = _days_in_week(week_param, VIDEO_EARLIEST)
            days_with_counts = []
            for d in reversed(w_days):
                count = _count_videos_for_day(d)
                if count > 0:
                    days_with_counts.append((d, count))
            from datetime import date as _date
            iso_year, iso_week = int(week_param[:4]), int(week_param.split('W')[1])
            thursday = _date.fromisocalendar(iso_year, iso_week, 4)
            month_str = thursday.strftime('%Y-%m')
            from routes.camera import render_videos_week
            html += render_videos_week('Sky Camera', week_param, days_with_counts,
                                        latest_path='../skycam', gallery_path='gallery',
                                        videos_path='videos', month_str=month_str)

        else:
            # Day view (default: today, falling back to most recent day with videos)
            if not day_param:
                day_param = _today_london()
                try:
                    day_dt = datetime.strptime(day_param, '%Y-%m-%d')
                except ValueError:
                    day_dt = datetime.utcnow()
                    day_param = day_dt.strftime('%Y-%m-%d')
                prefix = f"skycam/videos/{day_dt.strftime('%Y/%m/%d')}/"
                videos = _list_videos_for_prefix(prefix)
                # If today is empty, find the most recent day with videos using
                # delimiter-based S3 listing (3 requests: year→month→day) rather
                # than scanning backwards one day at a time (up to 30 requests).
                if not videos:
                    def _most_recent_prefix(prefix):
                        """Return the lexicographically last common prefix under prefix/."""
                        resp = s3.list_objects_v2(
                            Bucket=GARDENCAM_BUCKET, Prefix=prefix, Delimiter='/')
                        prefixes = [p['Prefix'] for p in resp.get('CommonPrefixes', [])]
                        return prefixes[-1] if prefixes else None
                    year_pfx  = _most_recent_prefix('skycam/videos/')
                    month_pfx = _most_recent_prefix(year_pfx)  if year_pfx  else None
                    day_pfx   = _most_recent_prefix(month_pfx) if month_pfx else None
                    if day_pfx:
                        videos = _list_videos_for_prefix(day_pfx)
                        # Parse YYYY/MM/DD from the prefix
                        parts = day_pfx.rstrip('/').split('/')
                        if len(parts) >= 3:
                            day_param = f"{parts[-3]}-{parts[-2]}-{parts[-1]}"
            else:
                try:
                    day_dt = datetime.strptime(day_param, '%Y-%m-%d')
                except ValueError:
                    day_dt = datetime.utcnow()
                    day_param = day_dt.strftime('%Y-%m-%d')
                prefix = f"skycam/videos/{day_dt.strftime('%Y/%m/%d')}/"
                videos = _list_videos_for_prefix(prefix)
            week_iso = _iso_week_for_date(day_param)
            try:
                skycam_stats = get_skycam_stats_for_date(day_param, thin_minutes=10)
            except Exception as e:
                print(f"skycam stats unavailable: {e}")
                skycam_stats = []
            from routes.camera import render_videos_day
            html += render_videos_day('Sky Camera', day_param, videos,
                                       latest_path='../skycam', gallery_path='gallery',
                                       videos_path='videos', week_iso=week_iso,
                                       exposure_data=skycam_stats)

    elif path == f'/{stage}/skycam/starcam' or path == '/skycam/starcam':
        # Starcam index: list all nights with stacked images
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        from collections import defaultdict
        nights = defaultdict(int)  # evening_date -> count

        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix='skycam/stacked/'):
            for obj in page.get('Contents', []):
                key = obj['Key']
                # Extract timestamp from filename: sky_YYYYMMDD_HHMMSS_stacked.jpg
                fname = key.rsplit('/', 1)[-1]
                if not fname.endswith('_stacked.jpg'):
                    continue
                ts_part = fname.replace('sky_', '').replace('_stacked.jpg', '')
                try:
                    ts = datetime.strptime(ts_part, '%Y%m%d_%H%M%S')
                    # Heuristic: UTC hour < 12 = belongs to previous evening
                    if ts.hour < 12:
                        evening = (ts - timedelta(days=1)).strftime('%Y-%m-%d')
                    else:
                        evening = ts.strftime('%Y-%m-%d')
                    nights[evening] += 1
                except ValueError:
                    pass

        sorted_nights = sorted(nights.items(), reverse=True)
        from routes.camera import render_starcam_index
        html += render_starcam_index(sorted_nights)

    elif path.startswith(f'/{stage}/skycam/starcam/night') or path.startswith('/skycam/starcam/night'):
        # Starcam night: show stacked images for a specific night
        query_params = event.get('queryStringParameters', {}) or {}
        evening_date = query_params.get('date', '')
        if not evening_date:
            html += '<p style="color:#888; text-align:center;">No date specified.</p>'
        else:
            s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
            from zoneinfo import ZoneInfo
            ev_dt = datetime.strptime(evening_date, '%Y-%m-%d')
            morning_dt = ev_dt + timedelta(days=1)

            # Search evening date (hours >= 12 UTC) and morning date (hours < 12 UTC)
            stacked = []
            for search_date, hour_filter in [(ev_dt, lambda h: h >= 12), (morning_dt, lambda h: h < 12)]:
                prefix = f"skycam/{search_date.strftime('%Y/%m/%d')}/"
                try:
                    paginator = s3.get_paginator('list_objects_v2')
                    for page in paginator.paginate(Bucket=GARDENCAM_BUCKET, Prefix=prefix):
                        for obj in page.get('Contents', []):
                            key = obj['Key']
                            if '_stacked.jpg' not in key:
                                continue
                            fname = key.rsplit('/', 1)[-1]
                            ts_part = fname.replace('sky_', '').replace('_stacked.jpg', '')
                            try:
                                ts = datetime.strptime(ts_part, '%Y%m%d_%H%M%S')
                                if hour_filter(ts.hour):
                                    local_ts = ts.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/London"))
                                    url = s3.generate_presigned_url(
                                        'get_object', Params={'Bucket': GARDENCAM_BUCKET, 'Key': key},
                                        ExpiresIn=7200)
                                    # Read S3 metadata for stats
                                    meta = {}
                                    try:
                                        head = s3.head_object(Bucket=GARDENCAM_BUCKET, Key=key)
                                        meta = head.get('Metadata', {})
                                    except Exception:
                                        pass
                                    local_h = local_ts.hour + local_ts.minute / 60
                                    delta = local_h if local_h < 12 else local_h - 24
                                    stacked.append({
                                        'url': url,
                                        'key': key,
                                        'timestamp': local_ts.strftime('%H:%M BST'),
                                        'sort_key': ts.isoformat(),
                                        'stack_count': meta.get('stack-count', ''),
                                        'darkest_100_avg': meta.get('darkest-100-avg', ''),
                                        'delta': round(delta, 2),
                                    })
                            except ValueError:
                                pass
                except Exception:
                    pass

            stacked.sort(key=lambda x: x.get('sort_key', x['timestamp']))

            # Query DynamoDB for hourly brightness through the night
            # Filenames are predictable: sky_YYYYMMDD_HH0000.jpg
            brightness_data = []
            try:
                from zoneinfo import ZoneInfo
                dynamodb = boto3.resource('dynamodb', region_name=GARDENCAM_REGION)
                stats_table = dynamodb.Table('gardencam-stats')
                # Evening hours (18-23 UTC on evening date) + morning hours (00-11 UTC on morning date)
                hours = [(ev_dt, h) for h in range(18, 24)] + [(morning_dt, h) for h in range(0, 12)]
                for dt, h in hours:
                    filename = f"sky_{dt.strftime('%Y%m%d')}_{h:02d}0000.jpg"
                    try:
                        resp = stats_table.get_item(Key={'filename': filename})
                        item = resp.get('Item')
                        if item:
                            avg_b = float(item.get('avg_brightness', 0))
                            utc_ts = datetime(dt.year, dt.month, dt.day, h, tzinfo=timezone.utc)
                            local_ts = utc_ts.astimezone(ZoneInfo("Europe/London"))
                            local_h = local_ts.hour + local_ts.minute / 60
                            delta = local_h if local_h < 12 else local_h - 24
                            brightness_data.append({
                                'time': local_ts.strftime('%H:%M'),
                                'value': round(avg_b, 1),
                                'sort_key': utc_ts.isoformat(),
                                'delta': round(delta, 2),
                            })
                    except Exception:
                        pass
                brightness_data.sort(key=lambda x: x['sort_key'])
            except Exception as e:
                print(f"Starcam brightness query failed: {e}")

            from routes.camera import render_starcam_night
            html += render_starcam_night(evening_date, stacked, brightness_data)

    elif path == f'/{stage}/skycam/clouds' or path == '/skycam/clouds':
        # "Clouds - The Movie" — playlist of hourly cloudcam videos with
        # day×hour selection, speed control, cast queue with auto-extend.
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)
        days = []
        today = datetime.utcnow()
        miss_streak = 0
        for back in range(0, 365):
            d = today - timedelta(days=back)
            ymd_path = d.strftime("%Y/%m/%d")
            ymd_flat = d.strftime("%Y%m%d")
            prefix = f"skycam/videos/{ymd_path}/"
            try:
                resp = s3.list_objects_v2(Bucket=GARDENCAM_BUCKET, Prefix=prefix)
            except Exception:
                resp = {}
            hours = []
            for obj in resp.get("Contents", []):
                k = obj["Key"]
                name = k.rsplit("/", 1)[-1]
                # sky_YYYYMMDD_HH.mp4 — the per-hour clips
                if not (name.startswith(f"sky_{ymd_flat}_") and name.endswith(".mp4")):
                    continue
                tag = name[len(f"sky_{ymd_flat}_"):-len(".mp4")]
                if not (len(tag) == 2 and tag.isdigit()):
                    continue   # skip _daily, _combined, _night, etc.
                hours.append({
                    "hh":      tag,
                    "url":     s3.generate_presigned_url(
                                  'get_object',
                                  Params={'Bucket': GARDENCAM_BUCKET, 'Key': k},
                                  ExpiresIn=14400),
                    "size_mb": round(obj["Size"] / 1024 / 1024, 1),
                })
            if hours:
                hours.sort(key=lambda h: h["hh"])
                days.append({
                    "date":  d.strftime("%Y-%m-%d"),
                    "hours": hours,
                })
                miss_streak = 0
            else:
                miss_streak += 1
                if miss_streak > 60:
                    break
        days.reverse()  # oldest first for chronological playback

        from routes.camera import render_clouds_movie
        return {
            'statusCode': 200,
            'body': render_clouds_movie(days),
            'headers': {'Content-Type': 'text/html; charset=utf-8'},
        }

    elif path.startswith(f'/{stage}/skycam/play') or path.startswith('/skycam/play'):
        query_params = event.get('queryStringParameters', {}) or {}
        s3 = boto3.client("s3", region_name=GARDENCAM_REGION)

        # Find the video to play: ?key=... or default to today's combined, falling back to daily
        video_key = query_params.get('key', '')
        if not video_key:
            today = datetime.utcnow()
            date_str = today.strftime('%Y%m%d')
            combined_key = f"skycam/videos/{today.strftime('%Y/%m/%d')}/sky_{date_str}_combined.mp4"
            daily_key = f"skycam/videos/{today.strftime('%Y/%m/%d')}/sky_{date_str}_daily.mp4"
            try:
                s3.head_object(Bucket=GARDENCAM_BUCKET, Key=combined_key)
                video_key = combined_key
            except Exception:
                video_key = daily_key

        try:
            s3.head_object(Bucket=GARDENCAM_BUCKET, Key=video_key)
            video_url = s3.generate_presigned_url(
                'get_object', Params={'Bucket': GARDENCAM_BUCKET, 'Key': video_key},
                ExpiresIn=7200)
            basename = video_key.rsplit('/', 1)[-1].replace('.mp4', '').replace('sky_', '')

            # Find the hourly segments for the clock overlay (convert UTC → London)
            from zoneinfo import ZoneInfo
            hours = []
            video_basename = video_key.rsplit('/', 1)[-1]
            is_multi = any(x in video_basename for x in ['_daily', '_combined', '_night'])

            if is_multi:
                # Daily/combined: list all hourly segments for the clock
                day_prefix = video_key.rsplit('/', 1)[0] + '/'
                try:
                    resp = s3.list_objects_v2(Bucket=GARDENCAM_BUCKET, Prefix=day_prefix)
                    for obj in sorted(resp.get('Contents', []), key=lambda o: o['Key']):
                        k = obj['Key']
                        if k.endswith('.mp4') and not any(x in k for x in ['_daily', '_combined', '_night']):
                            b = k.rsplit('/', 1)[-1].replace('.mp4', '').replace('sky_', '')
                            try:
                                h = datetime.strptime(b, '%Y%m%d_%H').replace(tzinfo=timezone.utc)
                                local_h = h.astimezone(ZoneInfo("Europe/London"))
                                hours.append(local_h.hour)
                            except ValueError:
                                pass
                except Exception:
                    pass
            else:
                # Single hourly video: just that hour
                b = video_basename.replace('.mp4', '').replace('sky_', '')
                try:
                    h = datetime.strptime(b, '%Y%m%d_%H').replace(tzinfo=timezone.utc)
                    local_h = h.astimezone(ZoneInfo("Europe/London"))
                    hours.append(local_h.hour)
                except ValueError:
                    pass

            from routes.camera import render_skycam_player
            html += render_skycam_player(video_url, basename, hours)
        except Exception as e:
            print(f"Error loading video for player: {e}")
            html += '<p style="color:#888; text-align:center; margin-top:3rem;">No daily video available yet today.</p>'

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

