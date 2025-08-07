# OBU Processing Service

Simple GPS data processor for active journey sessions.

## Overview

Processing Service quét journey sessions có status 'active' mỗi 15-20 giây và thu thập GPS data qua MQTT. Dữ liệu được lưu vào bảng `device_logs` với `journey_session_id`.

## Features

- ✅ **Simple & Clean**: Chỉ focus vào GPS data collection
- ✅ **Realtime Scanning**: Quét mỗi 15s cho map realtime
- ✅ **MQTT Integration**: Persistent connection, tham khảo api-service
- ✅ **Database Logging**: Lưu MQTT response vào device_logs.mqtt_response
- ✅ **Shared Config**: Dùng chung .env từ api-service
- ✅ **Detailed Logging**: Logger mỗi lần get data

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Scan Timer      │───▶│ Query Active    │───▶│ MQTT Request    │
│ (15s interval)  │    │ Journey Sessions│    │ GPS Data        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Filter Criteria │    │ Save to         │
                       │ start/end time  │    │ device_logs     │
                       │ status='active' │    │ + journey_id    │
                       └─────────────────┘    └─────────────────┘
```

## Configuration

Sử dụng chung `.env` từ `api-service`:

```bash
# Database
DATABASE_URL="postgresql://admin:password@localhost:5432/obu_service"

# MQTT
MQTT_BROKER_HOST=zxs-cs.netbodycamera.com
MQTT_BROKER_PORT=1883
MQTT_USERNAME=dev1
MQTT_PASSWORD=dev1
MQTT_USER_NO=kh4423
MQTT_TIMEOUT=10

# Processing (optional)
SCAN_INTERVAL=15  # seconds
MAX_CONCURRENT_DEVICES=5
```

## Installation & Run

```bash
# 1. Install dependencies
cd services/processing-service
pip install -r requirements.txt

# 2. Run service
python run.py
```

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `GET /status` - Processing status

## Data Flow

```
1. Timer triggers every 15s
   ↓
2. Query journey_sessions WHERE:
   - status = 'active'
   - start_time <= NOW <= end_time
   ↓
3. For each active session:
   - Get device_imei from vehicle->device
   - Send MQTT request: get-configs/GPS_INFO
   - Wait for MQTT response
   ↓
4. Save to device_logs:
   - journey_session_id
   - device_imei  
   - mqtt_response (full JSON)
   - collected_at
```

## Database Schema

```sql
device_logs:
- id (bigint, PK)
- journey_session_id (bigint, FK)
- device_imei (varchar 50)
- mqtt_response (jsonb) ← Full MQTT response
- collected_at (timestamptz)
```

## Logging

Service provides detailed logging:

```
🔍 Scanning for active journey sessions...
📋 Found 2 active sessions
📍 Collecting GPS for session 123 - Device 123456789 (29A-12345)
📤 MQTT request sent to 123456789 (session: abc123)
📥 MQTT response received from 123456789
✅ GPS data saved for session 123 - 123456789
💾 Device log saved: session=123, imei=123456789
```

## Monitoring

- **Health**: `GET /health`
- **Status**: `GET /status`
- **Logs**: Check console output for detailed processing info

Service runs on port **8001** (API service uses 8000).
