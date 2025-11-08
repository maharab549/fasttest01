from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Dict, Any, cast
from datetime import datetime, timedelta
from .. import auth, schemas, models
from ..database import get_db
import psutil
import time
import os

router = APIRouter(prefix="/admin/health", tags=["health"])

# Store server start time
SERVER_START_TIME = datetime.now()

@router.get("/status", response_model=Dict[str, Any])
def get_system_health(
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive system health metrics"""
    if not current_user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Server uptime
    uptime = datetime.now() - SERVER_START_TIME
    uptime_seconds = uptime.total_seconds()
    
    # CPU and Memory usage
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Network statistics
    try:
        net_io = psutil.net_io_counters()
        network_stats = {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024 * 1024), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024 * 1024), 2),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout
        }
    except:
        network_stats = None
    
    # Database health and statistics
    db_start = time.time()
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_latency = (time.time() - db_start) * 1000  # Convert to ms
        
        # Dialect-aware metadata queries
        bind = db.get_bind()
        dialect_name = getattr(getattr(bind, 'dialect', None), 'name', '') if bind else ''
        
        if dialect_name.startswith("postgresql"):
            # Database size
            db_size_bytes = db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
            # Table count in public schema
            tables_result = db.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).fetchall()
            table_count = len(tables_result)
        else:
            # Default to SQLite-compatible queries
            db_size_result = db.execute(text("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")).fetchone()
            db_size_bytes = db_size_result[0] if db_size_result else 0
            tables_result = db.execute(text("""
                SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            )).fetchall()
            table_count = len(tables_result)
        
        # Get record counts for key tables
        try:
            user_count = db.query(func.count(models.User.id)).scalar()
            product_count = db.query(func.count(models.Product.id)).scalar()
            order_count = db.query(func.count(models.Order.id)).scalar()
            
            # Active users (logged in within last 7 days)
            seven_days_ago = datetime.now() - timedelta(days=7)
            active_users = db.query(func.count(models.User.id)).filter(
                models.User.last_login >= seven_days_ago
            ).scalar() if hasattr(models.User, 'last_login') else 0
            
            # Recent orders (last 24 hours)
            one_day_ago = datetime.now() - timedelta(days=1)
            recent_orders = db.query(func.count(models.Order.id)).filter(
                models.Order.created_at >= one_day_ago
            ).scalar()
            
            # Pending orders
            pending_orders = db.query(func.count(models.Order.id)).filter(
                models.Order.status == 'pending'
            ).scalar()
            
            # Approved vs pending products
            approved_products = db.query(func.count(models.Product.id)).filter(
                models.Product.approval_status == 'approved'
            ).scalar()
            
            pending_products = db.query(func.count(models.Product.id)).filter(
                models.Product.approval_status == 'pending'
            ).scalar()
            
            record_counts = {
                "total_users": user_count,
                "total_products": product_count,
                "total_orders": order_count,
                "active_users_7d": active_users,
                "recent_orders_24h": recent_orders,
                "pending_orders": pending_orders,
                "approved_products": approved_products,
                "pending_products": pending_products
            }
        except Exception as e:
            record_counts = {"error": str(e)}
        
        db_status = "healthy"
    except Exception as e:
        db_latency = -1
        db_size_bytes = 0
        table_count = 0
        record_counts = {}
        db_status = f"unhealthy: {str(e)}"
    
    # Process information
    process = psutil.Process(os.getpid())
    process_memory = process.memory_info().rss
    process_cpu = process.cpu_percent(interval=0.1)
    
    # System load average
    try:
        getloadavg = getattr(os, "getloadavg", None)
        if callable(getloadavg):
            load_avg = cast(tuple[float, float, float], getloadavg())
            load_average = {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2),
                "15min": round(load_avg[2], 2)
            }
        else:
            load_average = None
    except (AttributeError, OSError):
        load_average = None
    
    # Check for potential issues
    issues = []
    if cpu_percent > 80:
        issues.append({"severity": "warning", "message": "High CPU usage detected"})
    if cpu_percent > 95:
        issues.append({"severity": "critical", "message": "Critical CPU usage"})
    if memory.percent > 80:
        issues.append({"severity": "warning", "message": "High memory usage detected"})
    if memory.percent > 95:
        issues.append({"severity": "critical", "message": "Critical memory usage"})
    if disk.percent > 85:
        issues.append({"severity": "warning", "message": "Disk space running low"})
    if disk.percent > 95:
        issues.append({"severity": "critical", "message": "Critical disk space"})
    if db_latency > 100:
        issues.append({"severity": "warning", "message": f"High database latency: {db_latency:.2f}ms"})
    if db_latency > 500:
        issues.append({"severity": "critical", "message": f"Critical database latency: {db_latency:.2f}ms"})
    
    # Overall health status
    critical_issues = [i for i in issues if i["severity"] == "critical"]
    warning_issues = [i for i in issues if i["severity"] == "warning"]
    
    if critical_issues:
        overall_status = "critical"
    elif warning_issues:
        overall_status = "warning"
    elif db_status == "healthy":
        overall_status = "healthy"
    else:
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "server": {
            "start_time": SERVER_START_TIME.isoformat(),
            "uptime_seconds": int(uptime_seconds),
            "process_id": os.getpid(),
            "process_memory_bytes": process_memory,
            "process_cpu_percent": round(process_cpu, 2)
        },
        "system": {
            "cpu_usage_percent": round(cpu_percent, 2),
            "cpu_count": cpu_count,
            "load_average": load_average,
            "memory_usage_percent": round(memory.percent, 2),
            "memory_total_bytes": memory.total,
            "memory_used_bytes": memory.used,
            "memory_available_bytes": memory.available,
            "disk_usage_percent": round(disk.percent, 2),
            "disk_total_bytes": disk.total,
            "disk_used_bytes": disk.used,
            "disk_free_bytes": disk.free
        },
        "network": network_stats,
        "database": {
            "status": db_status,
            "latency_ms": round(db_latency, 2) if db_latency > 0 else None,
            "size_bytes": db_size_bytes,
            "table_count": table_count,
            "records": record_counts
        },
        "issues": issues,
        "metrics_summary": {
            "total_issues": len(issues),
            "critical_issues": len(critical_issues),
            "warning_issues": len(warning_issues)
        }
    }

@router.get("/metrics", response_model=Dict[str, Any])
def get_system_metrics(
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed system metrics over time"""
    if not current_user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # This could be extended to track metrics over time
    # i will update it later in winter vacation
    health_data = get_system_health(current_user, db)
    
    return {
        "current": health_data,
        "history": []  # Could be populated from a metrics table
    }
