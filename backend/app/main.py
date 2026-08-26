from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import math
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger('mineguard')
UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
APP_ENV=os.getenv('APP_ENV','development').lower()
DB_URL = os.getenv('DATABASE_URL') or os.getenv('MINEGUARD_DATABASE_URL', f'sqlite:///{DATA / "mineguard.db"}')
if DB_URL.startswith('postgres://'): DB_URL='postgresql+psycopg://'+DB_URL.removeprefix('postgres://')
elif DB_URL.startswith('postgresql://'): DB_URL='postgresql+psycopg://'+DB_URL.removeprefix('postgresql://')
engine = create_engine(DB_URL, connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite') else {}, poolclass=StaticPool if DB_URL=='sqlite:///:memory:' else None, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase): pass


class Node(Base):
    __tablename__ = 'sensor_nodes'
    id: Mapped[int] = mapped_column(primary_key=True)
    node_code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    source_type: Mapped[str] = mapped_column(String(16), default='simulated')
    source_label: Mapped[str] = mapped_column(String(60), default='SIMULATED')
    connection_status: Mapped[str] = mapped_column(String(20), default='online')
    sensor_health: Mapped[str] = mapped_column(String(20), default='normal')
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sequence: Mapped[int] = mapped_column(Integer, default=-1)
    risk_score: Mapped[float] = mapped_column(Float, default=10)
    risk_class: Mapped[str] = mapped_column(String(20), default='safe')
    displacement_mm: Mapped[float] = mapped_column(Float, default=0)
    movement_rate: Mapped[float] = mapped_column(Float, default=0)
    tilt_x: Mapped[float] = mapped_column(Float, default=0)
    tilt_y: Mapped[float] = mapped_column(Float, default=0)
    vibration: Mapped[float] = mapped_column(Float, default=.05)
    moisture: Mapped[float] = mapped_column(Float, default=30)
    battery: Mapped[float] = mapped_column(Float, default=90)
    rssi: Mapped[float] = mapped_column(Float, default=-70)
    vibration_peak: Mapped[float] = mapped_column(Float, default=.12)
    soil_pressure: Mapped[float] = mapped_column(Float, default=12)
    rainfall: Mapped[float] = mapped_column(Float, default=0)
    temperature: Mapped[float] = mapped_column(Float, default=31)
    humidity: Mapped[float] = mapped_column(Float, default=65)
    battery_voltage: Mapped[float] = mapped_column(Float, default=3.9)
    snr: Mapped[float] = mapped_column(Float, default=7)
    data_quality: Mapped[float] = mapped_column(Float, default=100)
    sector_id: Mapped[int | None] = mapped_column(ForeignKey('mine_sectors.id'), nullable=True)
    nearest_landmark_id: Mapped[int | None] = mapped_column(ForeignKey('mine_landmarks.id'), nullable=True)
    landmark_distance_m: Mapped[float] = mapped_column(Float, default=0)
    landmark_bearing_deg: Mapped[float] = mapped_column(Float, default=0)
    installation_location_type: Mapped[str] = mapped_column(String(30), default='surface')
    installation_depth_m: Mapped[float] = mapped_column(Float, default=0)
    mounting_height_m: Mapped[float] = mapped_column(Float, default=1.2)
    local_x_m: Mapped[float] = mapped_column(Float, default=0)
    local_y_m: Mapped[float] = mapped_column(Float, default=0)
    local_z_m: Mapped[float] = mapped_column(Float, default=0)
    position_accuracy_m: Mapped[float] = mapped_column(Float, default=3)
    gateway_id: Mapped[int | None] = mapped_column(ForeignKey('gateways.id'), nullable=True)
    configured_communication_range_m: Mapped[float] = mapped_column(Float, default=500)
    estimated_communication_range_m: Mapped[float] = mapped_column(Float, default=350)
    coverage_status: Mapped[str] = mapped_column(String(30), default='active')
    installation_notes: Mapped[str] = mapped_column(String(500), default='Demonstration placement')
    last_location_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    readings: Mapped[list['Reading']] = relationship(cascade='all, delete-orphan')


class MineSector(Base):
    __tablename__='mine_sectors'
    id:Mapped[int]=mapped_column(primary_key=True); mine_id:Mapped[str]=mapped_column(String(32),default='demo')
    sector_code:Mapped[str]=mapped_column(String(30),unique=True); name:Mapped[str]=mapped_column(String(100)); sector_type:Mapped[str]=mapped_column(String(40)); level_name:Mapped[str]=mapped_column(String(60)); depth_m:Mapped[float]=mapped_column(Float,default=0); risk_level:Mapped[str]=mapped_column(String(20),default='safe'); boundary_geojson:Mapped[str]=mapped_column(String(2000)); description:Mapped[str]=mapped_column(String(500)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True)); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))

class MineLandmark(Base):
    __tablename__='mine_landmarks'
    id:Mapped[int]=mapped_column(primary_key=True); mine_id:Mapped[str]=mapped_column(String(32),default='demo'); sector_id:Mapped[int]=mapped_column(ForeignKey('mine_sectors.id')); landmark_code:Mapped[str]=mapped_column(String(30),unique=True); name:Mapped[str]=mapped_column(String(100)); landmark_type:Mapped[str]=mapped_column(String(50)); latitude:Mapped[float]=mapped_column(Float); longitude:Mapped[float]=mapped_column(Float); local_x_m:Mapped[float]=mapped_column(Float,default=0); local_y_m:Mapped[float]=mapped_column(Float,default=0); local_z_m:Mapped[float]=mapped_column(Float,default=0); depth_m:Mapped[float]=mapped_column(Float,default=0); description:Mapped[str]=mapped_column(String(500)); icon_type:Mapped[str]=mapped_column(String(30),default='landmark'); enabled:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True)); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))

class Gateway(Base):
    __tablename__='gateways'
    id:Mapped[int]=mapped_column(primary_key=True); gateway_code:Mapped[str]=mapped_column(String(30),unique=True); name:Mapped[str]=mapped_column(String(100)); latitude:Mapped[float]=mapped_column(Float); longitude:Mapped[float]=mapped_column(Float); local_x_m:Mapped[float]=mapped_column(Float,default=0); local_y_m:Mapped[float]=mapped_column(Float,default=0); status:Mapped[str]=mapped_column(String(20),default='online'); configured_range_m:Mapped[float]=mapped_column(Float,default=800); last_seen:Mapped[datetime]=mapped_column(DateTime(timezone=True))


class Reading(Base):
    __tablename__ = 'sensor_readings'
    __table_args__ = (UniqueConstraint('node_id', 'sequence_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey('sensor_nodes.id'))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sequence_id: Mapped[int] = mapped_column(Integer)
    displacement_mm: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    risk_class: Mapped[str] = mapped_column(String(20))
    movement_rate: Mapped[float] = mapped_column(Float, default=0)
    tilt_x: Mapped[float] = mapped_column(Float, default=0)
    tilt_y: Mapped[float] = mapped_column(Float, default=0)
    vibration: Mapped[float] = mapped_column(Float, default=0)
    vibration_peak: Mapped[float] = mapped_column(Float, default=0)
    moisture: Mapped[float] = mapped_column(Float, default=0)
    soil_pressure: Mapped[float] = mapped_column(Float, default=0)
    rainfall: Mapped[float] = mapped_column(Float, default=0)
    temperature: Mapped[float] = mapped_column(Float, default=0)
    humidity: Mapped[float] = mapped_column(Float, default=0)
    battery: Mapped[float] = mapped_column(Float, default=0)
    battery_voltage: Mapped[float] = mapped_column(Float, default=0)
    rssi: Mapped[float] = mapped_column(Float, default=0)
    snr: Mapped[float] = mapped_column(Float, default=0)
    data_quality: Mapped[float] = mapped_column(Float, default=100)


class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[int] = mapped_column(primary_key=True)
    node_code: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(30), default='ground-risk')
    status: Mapped[str] = mapped_column(String(20), default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Telemetry(BaseModel):
    node_id: str = Field(pattern=r'^NODE-\d{2}$')
    timestamp: datetime
    sequence_id: int = Field(ge=0)
    source_type: Literal['real', 'simulated']
    displacement_mm: float = Field(ge=-100, le=100)
    tilt_x_deg: float = Field(ge=-45, le=45)
    tilt_y_deg: float = Field(ge=-45, le=45)
    vibration_rms: float = Field(ge=0, le=20)
    vibration_peak: float = Field(ge=0, le=50)
    soil_moisture_percent: float = Field(ge=0, le=100)
    soil_pressure: float = Field(ge=0, le=1000)
    rainfall_mm: float = Field(ge=0, le=1000)
    temperature_c: float = Field(ge=-30, le=80)
    humidity_percent: float = Field(ge=0, le=100)
    battery_voltage: float = Field(ge=0, le=6)
    battery_percentage: float = Field(ge=0, le=100)
    rssi: float = Field(ge=-150, le=0)
    snr: float = Field(ge=-30, le=30)
    sensor_health: Literal['normal', 'degraded', 'failed'] = 'normal'
    data_quality_score: float = Field(default=100, ge=0, le=100)

    @field_validator('timestamp')
    @classmethod
    def utc_required(cls, v: datetime):
        if v.tzinfo is None: raise ValueError('timestamp must include timezone')
        return v.astimezone(UTC)


class SimCommand(BaseModel):
    scenario: Literal['normal','gradual_subsidence','sudden_movement','heavy_rainfall','abnormal_vibration','correlated_movement','weak_signal','low_battery','sensor_drift','node_offline','sensor_failure','recovery']
    intensity: float = Field(1, ge=.1, le=3)
    speed: float = Field(1, ge=.25, le=4)
    node_code: str = 'all'

class PlacementUpdate(BaseModel):
    sector_id:int=Field(gt=0); nearest_landmark_id:int=Field(gt=0); landmark_distance_m:float=Field(ge=0,le=10000); landmark_bearing_deg:float=Field(ge=0,lt=360); gateway_id:int=Field(gt=0); configured_communication_range_m:float=Field(gt=0,le=20000); installation_depth_m:float=Field(ge=0,le=3000); local_x_m:float=Field(ge=-100000,le=100000); local_y_m:float=Field(ge=-100000,le=100000); local_z_m:float=Field(ge=-5000,le=5000); installation_notes:str=Field(max_length=500)


# Prototype-only analytical policy. Kept server-side so clients never embed safety
# thresholds and can be replaced by a mine-specific, independently validated policy.
SENSOR_CONFIG = {
    'displacement_mm': {'label':'Displacement','unit':'mm','mode':'absolute','observation':3,'warning':5,'critical':9,'rate':1,'normal_range':[-3,3]},
    'movement_rate_mm_per_hour': {'label':'Movement rate','unit':'mm/h','mode':'absolute','observation':.6,'warning':1.2,'critical':2.5,'rate':.5,'normal_range':[-.6,.6]},
    'tilt_x_deg': {'label':'Tilt X','unit':'°','mode':'absolute','observation':1.5,'warning':3,'critical':6,'rate':.5,'normal_range':[-1.5,1.5]},
    'tilt_y_deg': {'label':'Tilt Y','unit':'°','mode':'absolute','observation':1.5,'warning':3,'critical':6,'rate':.5,'normal_range':[-1.5,1.5]},
    'vibration_rms': {'label':'Vibration RMS','unit':'g','mode':'high','observation':.4,'warning':1.2,'critical':2.5,'rate':.4,'normal_range':[0,.4]},
    'vibration_peak': {'label':'Vibration peak','unit':'g','mode':'high','observation':1,'warning':3,'critical':6,'rate':1,'normal_range':[0,1]},
    'soil_moisture_percent': {'label':'Soil moisture','unit':'%','mode':'high','observation':55,'warning':70,'critical':85,'rate':8,'normal_range':[20,55]},
    'soil_pressure': {'label':'Soil pressure','unit':'kPa','mode':'high','observation':150,'warning':250,'critical':400,'rate':30,'normal_range':[0,150]},
    'rainfall_mm': {'label':'Rainfall','unit':'mm','mode':'high','observation':25,'warning':50,'critical':100,'rate':20,'normal_range':[0,25]},
    'temperature_c': {'label':'Temperature','unit':'°C','mode':'high','observation':40,'warning':50,'critical':60,'rate':5,'normal_range':[-10,40]},
    'humidity_percent': {'label':'Humidity','unit':'%','mode':'high','observation':75,'warning':88,'critical':96,'rate':10,'normal_range':[10,75]},
    'battery_percentage': {'label':'Battery','unit':'%','mode':'low','observation':35,'warning':20,'critical':10,'rate':10,'normal_range':[35,100]},
    'rssi': {'label':'RSSI','unit':'dBm','mode':'low','observation':-95,'warning':-110,'critical':-125,'rate':15,'normal_range':[-95,0]},
    'snr': {'label':'SNR','unit':'dB','mode':'low','observation':3,'warning':0,'critical':-8,'rate':4,'normal_range':[3,30]},
}
ANALYTICS_POLICY = {'stale_seconds':120,'minimum_data_quality':60,'weights':{'displacement_mm':.24,'movement_rate_mm_per_hour':.18,'tilt':.13,'vibration':.12,'moisture':.08,'soil_pressure':.06,'neighbour_agreement':.07,'ml_probability':.08,'data_quality':.02,'sensor_health':.02}}

def sensor_level(value: float, cfg: dict) -> tuple[str,float,float]:
    v=abs(value) if cfg['mode']=='absolute' else value
    levels=(('Critical',cfg['critical'],100),('Warning',cfg['warning'],72),('Observation',cfg['observation'],48))
    for name,threshold,score in levels:
        crossed = v <= threshold if cfg['mode']=='low' else v >= threshold
        if crossed: return name,score,threshold
    return 'Normal',min(35,abs(v)/(abs(cfg['observation']) or 1)*35),cfg['observation']

def sensor_rows(n: Node) -> list[dict]:
    values={k:getattr(n, {'movement_rate_mm_per_hour':'movement_rate','tilt_x_deg':'tilt_x','tilt_y_deg':'tilt_y','vibration_rms':'vibration','soil_moisture_percent':'moisture','rainfall_mm':'rainfall','temperature_c':'temperature','humidity_percent':'humidity','battery_percentage':'battery'}.get(k,k)) for k in SENSOR_CONFIG}
    stale=not n.last_seen or (datetime.now(UTC)-(n.last_seen.replace(tzinfo=UTC) if n.last_seen.tzinfo is None else n.last_seen)).total_seconds()>ANALYTICS_POLICY['stale_seconds']
    result=[]
    for key,cfg in SENSOR_CONFIG.items():
        value=values[key]; level,score,threshold=sensor_level(value,cfg)
        if n.connection_status=='offline': level='Offline'
        elif n.sensor_health=='failed': level='Sensor Failure'
        elif stale: level='Stale'
        elif n.data_quality<ANALYTICS_POLICY['minimum_data_quality']: level='Insufficient Data'
        direction='stable' if abs(value)<.01 else ('decreasing' if value<0 else 'increasing')
        result.append({'sensor':key,'label':cfg['label'],'value':round(value,2),'unit':cfg['unit'],'risk_score':round(score,1),'risk_level':level,'trend':direction,'change_1h':round(n.movement_rate if key=='displacement_mm' else 0,2),'threshold':threshold,'thresholds':{x:cfg[x] for x in ('observation','warning','critical')},'data_quality':round(n.data_quality,1),'anomaly_score':round(max(score,n.risk_score*.72),1),'last_reading':n.last_seen.isoformat().replace('+00:00','Z') if n.last_seen else None,'explanation':f"{cfg['label']} is {value:.2f} {cfg['unit']}; analytical status is {level} against the {threshold:g} {cfg['unit']} threshold."})
    return result


class Hub:
    def __init__(self): self.clients: set[WebSocket] = set(); self.seq = 0
    async def connect(self, ws): await ws.accept(); self.clients.add(ws)
    def remove(self, ws): self.clients.discard(ws)
    async def publish(self, event):
        self.seq += 1; event['message_sequence'] = self.seq
        dead=[]
        for ws in tuple(self.clients):
            try: await ws.send_json(event)
            except Exception: dead.append(ws)
        for ws in dead: self.remove(ws)

hub = Hub()
sim_task: asyncio.Task | None = None
sim_state = {'running': False, 'scenario': 'normal', 'intensity': 1.0, 'speed': 1.0, 'node_code': 'all'}


def classify(score: float, previous: str = 'safe') -> str:
    boundaries = [('safe',40),('observation',60),('warning',80),('critical',101)]
    raw = next(name for name, upper in boundaries if score <= upper)
    rank = {n:i for i,(n,_) in enumerate(boundaries)}
    if raw != previous and abs(rank[raw]-rank.get(previous,0)) == 1:
        threshold = [40,60,80][min(rank[raw], rank.get(previous,0))]
        if raw == previous: return raw
        if rank[raw] > rank.get(previous,0) and score < threshold + 4: return previous
        if rank[raw] < rank.get(previous,0) and score > threshold - 4: return previous
    return raw


def risk(t: Telemetry, previous='safe'):
    score = min(100, abs(t.displacement_mm)*5 + abs(t.tilt_x_deg)*5 + abs(t.tilt_y_deg)*3 + t.vibration_rms*12 + max(0,t.soil_moisture_percent-50)*.7 + (100-t.data_quality_score)*.1)
    return round(score,1), classify(score, previous)


def node_dict(n: Node):
    ts = n.last_seen.isoformat().replace('+00:00','Z') if n.last_seen else None
    region='North Sector' if n.latitude>=23.7955 else 'South Sector'; zone='Subsidence Zone' if n.longitude>=86.4305 else 'Gateway Zone'
    return {'node_code':n.node_code,'name':n.name,'mine_name':'MineGuard Demonstration Mine','region':region,'zone':zone,'latitude':n.latitude,'longitude':n.longitude,'installation_position':'Surface monitoring point','firmware_version':'MG-1.4.2','source_type':n.source_type,'source_label':n.source_label,'connection_status':n.connection_status,'communication_status':'weak' if n.rssi<-110 else n.connection_status,'sensor_health':n.sensor_health,'hardware_health_score':100 if n.sensor_health=='normal' else (55 if n.sensor_health=='degraded' else 10),'last_seen':ts,'risk_score':n.risk_score,'risk_class':n.risk_class,'displacement_mm':n.displacement_mm,'movement_rate_mm_per_hour':n.movement_rate,'tilt_x_deg':n.tilt_x,'tilt_y_deg':n.tilt_y,'vibration_rms':n.vibration,'vibration_peak':n.vibration_peak,'soil_moisture_percent':n.moisture,'soil_pressure':n.soil_pressure,'rainfall_mm':n.rainfall,'temperature_c':n.temperature,'humidity_percent':n.humidity,'battery_voltage':n.battery_voltage,'battery_percentage':n.battery,'rssi':n.rssi,'snr':n.snr,'data_quality_score':n.data_quality,'prediction':round(n.displacement_mm*1.25,2),'confidence':round(max(20,n.data_quality*.88),1),'active_alert_count':0}


def seed():
    Base.metadata.create_all(engine)
    # Lightweight additive migration for existing prototype SQLite databases.
    if DB_URL.startswith('sqlite'):
        node_columns={'vibration_peak':'.12','soil_pressure':'12','rainfall':'0','temperature':'31','humidity':'65','battery_voltage':'3.9','snr':'7','sector_id':'NULL','nearest_landmark_id':'NULL','landmark_distance_m':'0','landmark_bearing_deg':'0','installation_location_type':"'surface'",'installation_depth_m':'0','mounting_height_m':'1.2','local_x_m':'0','local_y_m':'0','local_z_m':'0','position_accuracy_m':'3','gateway_id':'NULL','configured_communication_range_m':'500','estimated_communication_range_m':'350','coverage_status':"'active'",'installation_notes':"'Demonstration placement'",'last_location_verified_at':'NULL'}
        reading_columns={'movement_rate':'0','tilt_x':'0','tilt_y':'0','vibration':'0','vibration_peak':'0','moisture':'0','soil_pressure':'0','rainfall':'0','temperature':'0','humidity':'0','battery':'0','battery_voltage':'0','rssi':'0','snr':'0','data_quality':'100'}
        with engine.begin() as conn:
            for table,columns in [('sensor_nodes',node_columns),('sensor_readings',reading_columns)]:
                existing={r[1] for r in conn.execute(text(f'PRAGMA table_info({table})'))}
                for name,default in columns.items():
                    if name not in existing:
                        column_type='VARCHAR(500)' if name in ('installation_location_type','coverage_status','installation_notes') else ('DATETIME' if name=='last_location_verified_at' else 'FLOAT')
                        nullable='' if default!='NULL' else ''
                        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {column_type} DEFAULT {default} {nullable}'))
    with Session() as db:
        now=datetime.now(UTC)
        if not db.scalar(select(MineSector.id).limit(1)):
            sectors=[
              ('SEC-N','North Subsidence','subsidence-zone','Surface',0,'warning',[[[86.4295,23.7954],[86.4312,23.7954],[86.4312,23.7966],[86.4295,23.7966],[86.4295,23.7954]]]),
              ('SEC-S','South Monitoring','surface','Surface',0,'safe',[[[86.4292,23.7944],[86.4318,23.7944],[86.4318,23.7954],[86.4292,23.7954],[86.4292,23.7944]]]),
              ('UG-P1','Underground Panel 1','underground-panel','Level -120 m',120,'observation',[[[86.4302,23.7948],[86.4312,23.7948],[86.4312,23.7953],[86.4302,23.7953],[86.4302,23.7948]]]),
              ('INF-E','Eastern Infrastructure','infrastructure-zone','Surface',0,'safe',[[[86.4312,23.7953],[86.4320,23.7953],[86.4320,23.7963],[86.4312,23.7963],[86.4312,23.7953]]])]
            for code,name,stype,level,depth,risk_level,coords in sectors: db.add(MineSector(mine_id='demo',sector_code=code,name=name,sector_type=stype,level_name=level,depth_m=depth,risk_level=risk_level,boundary_geojson=json.dumps({'type':'Polygon','coordinates':coords}),description=f'Demonstration {stype} sector',created_at=now,updated_at=now))
            db.flush()
        sectors={s.sector_code:s for s in db.scalars(select(MineSector))}
        if not db.scalar(select(Gateway.id).limit(1)): db.add(Gateway(gateway_code='GW-01',name='North LoRa Gateway',latitude=23.7960,longitude=86.4301,local_x_m=0,local_y_m=0,status='online',configured_range_m=800,last_seen=now));db.flush()
        gateway=db.scalar(select(Gateway).limit(1))
        if not db.scalar(select(MineLandmark.id).limit(1)):
            landmarks=[('LM-ENT','Main Mine Entrance','mine entrance','SEC-S',23.79465,86.42955,0,0),('LM-VENT','Ventilation Shaft','ventilation shaft','SEC-N',23.79625,86.43005,0,0),('LM-GW','Gateway Tower','gateway tower','SEC-N',23.7960,86.4301,0,0),('LM-J1','Junction J-1','underground junction','UG-P1',23.7950,86.43045,32,18),('LM-PUMP','Pump Station','pump station','UG-P1',23.7951,86.43095,85,26),('LM-REF','Subsidence Reference','subsidence reference point','INF-E',23.79585,86.43155,0,0),('LM-PLAT','Movable Demo Platform','movable demonstration platform','SEC-S',23.7949,86.4303,0,0)]
            for code,name,ltype,sector,lat,lng,x,y in landmarks: db.add(MineLandmark(mine_id='demo',sector_id=sectors[sector].id,landmark_code=code,name=name,landmark_type=ltype,latitude=lat,longitude=lng,local_x_m=x,local_y_m=y,local_z_m=-sectors[sector].depth_m,depth_m=sectors[sector].depth_m,description=f'Known demonstration reference: {name}',icon_type=ltype.replace(' ','-'),enabled=True,created_at=now,updated_at=now))
            db.flush()
        landmarks={l.landmark_code:l for l in db.scalars(select(MineLandmark))}
        existing=list(db.scalars(select(Node).order_by(Node.node_code)))
        if not existing:
            coords=[(23.7957,86.4304),(23.7962,86.4310),(23.7951,86.43075),(23.79565,86.43155)]
            for i,(lat,lng) in enumerate(coords,1): db.add(Node(node_code=f'NODE-{i:02}',name=f'Sensor Device {i}',latitude=lat,longitude=lng,source_type='real' if i==1 else 'simulated',source_label='REAL' if i==1 else 'SIMULATED'))
            db.flush();existing=list(db.scalars(select(Node).order_by(Node.node_code)))
        placements=[('SEC-N','LM-VENT',42,132,'surface',0,120,75,'active'),('SEC-N','LM-GW',96,88,'surface',0,220,135,'weak'),('UG-P1','LM-J1',38,74,'underground',120,180,95,'active'),('INF-E','LM-REF',28,205,'surface',0,420,310,'gap-edge')]
        for n,p in zip(existing,placements):
            sec,lm,dist,bearing,kind,depth,configured,estimated,cstatus=p;n.sector_id=sectors[sec].id;n.nearest_landmark_id=landmarks[lm].id;n.landmark_distance_m=dist;n.landmark_bearing_deg=bearing;n.installation_location_type=kind;n.installation_depth_m=depth;n.local_x_m=landmarks[lm].local_x_m+dist*math.sin(math.radians(bearing));n.local_y_m=landmarks[lm].local_y_m+dist*math.cos(math.radians(bearing));n.local_z_m=-depth;n.gateway_id=gateway.id;n.configured_communication_range_m=configured;n.estimated_communication_range_m=estimated;n.coverage_status=cstatus;n.last_location_verified_at=now
        existing[0].source_type='real';existing[0].source_label='REAL (demonstration device)'
        for n in existing[1:]:n.source_type='simulated';n.source_label='SIMULATED'
        if len(existing)>1: existing[1].rssi=-116;existing[1].snr=-2
        if len(existing)>3: existing[3].connection_status='offline'
        db.commit()


async def ingest(t: Telemetry):
    with Session() as db:
        n=db.scalar(select(Node).where(Node.node_code==t.node_id))
        if not n: raise HTTPException(404,'Unknown node')
        existing=db.scalar(select(Reading).where(Reading.node_id==n.id,Reading.sequence_id==t.sequence_id))
        if existing: return {'duplicate':True,'node':node_dict(n)}
        if t.sequence_id <= n.last_sequence: raise HTTPException(409,'Out-of-order sequence')
        old=n.displacement_mm; score,level=risk(t,n.risk_class)
        hours=max((t.timestamp-(n.last_seen.replace(tzinfo=UTC) if n.last_seen and n.last_seen.tzinfo is None else n.last_seen or t.timestamp)).total_seconds()/3600,1/3600)
        movement=(t.displacement_mm-old)/hours
        n.last_sequence=t.sequence_id; n.last_seen=t.timestamp; n.source_type=t.source_type; n.source_label=t.source_type.upper(); n.connection_status='online'; n.sensor_health=t.sensor_health; n.risk_score=score; n.risk_class=level; n.displacement_mm=t.displacement_mm; n.movement_rate=movement; n.tilt_x=t.tilt_x_deg; n.tilt_y=t.tilt_y_deg; n.vibration=t.vibration_rms; n.vibration_peak=t.vibration_peak; n.moisture=t.soil_moisture_percent; n.soil_pressure=t.soil_pressure; n.rainfall=t.rainfall_mm; n.temperature=t.temperature_c; n.humidity=t.humidity_percent; n.battery_voltage=t.battery_voltage; n.battery=t.battery_percentage; n.rssi=t.rssi; n.snr=t.snr; n.data_quality=t.data_quality_score
        db.add(Reading(node_id=n.id,timestamp=t.timestamp,sequence_id=t.sequence_id,displacement_mm=t.displacement_mm,risk_score=score,risk_class=level,movement_rate=movement,tilt_x=t.tilt_x_deg,tilt_y=t.tilt_y_deg,vibration=t.vibration_rms,vibration_peak=t.vibration_peak,moisture=t.soil_moisture_percent,soil_pressure=t.soil_pressure,rainfall=t.rainfall_mm,temperature=t.temperature_c,humidity=t.humidity_percent,battery=t.battery_percentage,battery_voltage=t.battery_voltage,rssi=t.rssi,snr=t.snr,data_quality=t.data_quality_score))
        if level in ('warning','critical'):
            cutoff=time.time()-60
            recent=db.scalar(select(Alert).where(Alert.node_code==n.node_code,Alert.severity==level,Alert.status=='open').order_by(Alert.id.desc()))
            if not recent or recent.created_at.replace(tzinfo=UTC).timestamp() < cutoff:
                db.add(Alert(node_code=n.node_code,severity=level,title=f'{level.title()} ground movement',message=f'{n.node_code}: {t.displacement_mm:.1f} mm displacement; hybrid risk {score:.0f}/100.',created_at=datetime.now(UTC)))
        db.commit(); payload=node_dict(n)
    await hub.publish({'type':'telemetry','node':payload})
    return {'duplicate':False,'node':payload}


async def simulator_loop():
    sequence=int(time.time())
    while sim_state['running']:
        sequence += 1
        with Session() as db: nodes=list(db.scalars(select(Node)))
        for i,n in enumerate(nodes):
            if sim_state['node_code'] not in ('all',n.node_code): continue
            s=sim_state['scenario']; k=sim_state['intensity']; now=datetime.now(UTC); d=n.displacement_mm; vib=.05; moist=n.moisture; batt=n.battery; rssi=-70; health='normal'; quality=100
            if s=='normal' or s=='recovery': d=d*.75; moist=max(32,moist-.5)
            elif s=='gradual_subsidence': d=max(-20,d-.35*k*(1 if i<3 else .5))
            elif s=='sudden_movement': d=max(-20,d-4*k); vib=2.4*k
            elif s=='heavy_rainfall': moist=min(100,moist+3*k); d=max(-20,d-.12*k)
            elif s=='abnormal_vibration': vib=3.2*k
            elif s=='correlated_movement': d=max(-20,d-.28*k)
            elif s=='weak_signal': rssi=-125
            elif s=='low_battery': batt=max(0,batt-5*k)
            elif s=='sensor_drift': d=max(-20,d-.1*k*(i+1)); quality=65
            elif s=='sensor_failure': health='failed'; quality=25
            if s=='node_offline':
                with Session() as db:
                    x=db.scalar(select(Node).where(Node.node_code==n.node_code)); x.connection_status='offline'; db.commit(); payload=node_dict(x)
                await hub.publish({'type':'telemetry','node':payload}); continue
            t=Telemetry(node_id=n.node_code,timestamp=now,sequence_id=sequence*10+i,source_type='simulated',displacement_mm=d,tilt_x_deg=min(12,abs(d)*.25),tilt_y_deg=min(8,abs(d)*.12),vibration_rms=vib,vibration_peak=vib*2.5,soil_moisture_percent=moist,soil_pressure=12,rainfall_mm=20 if s=='heavy_rainfall' else 0,temperature_c=31,humidity_percent=65,battery_voltage=3.8,battery_percentage=batt,rssi=rssi,snr=7,sensor_health=health,data_quality_score=quality)
            await ingest(t)
        await asyncio.sleep(max(.25,2/sim_state['speed']))


@asynccontextmanager
async def lifespan(app):
    seed(); yield
    global sim_task
    if sim_task: sim_task.cancel()

app=FastAPI(title='MineGuard AI',version='1.0.0',lifespan=lifespan)
cors_raw=os.getenv('CORS_ORIGINS') or os.getenv('MINEGUARD_CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in cors_raw.split(',') if x.strip()],allow_methods=['*'],allow_headers=['*'])

@app.middleware('http')
async def correlation(request:Request,call_next):
    cid=request.headers.get('x-correlation-id',str(uuid.uuid4())); started=time.perf_counter()
    try: response=await call_next(request)
    except Exception as exc:
        log.exception(json.dumps({'event':'request_failed','correlation_id':cid,'path':request.url.path})); return JSONResponse({'detail':'Internal server error','correlation_id':cid},500)
    response.headers['x-correlation-id']=cid; log.info(json.dumps({'event':'request','correlation_id':cid,'path':request.url.path,'status':response.status_code,'ms':round((time.perf_counter()-started)*1000,1)})); return response

@app.get('/health')
def health():
    try:
        with Session() as db: db.execute(select(1)); database='healthy'
    except Exception: database='unhealthy'
    return {'status':'ok' if database=='healthy' else 'degraded','database':database,'mqtt':'disabled','ml':'rule-based fallback active','websocket_connections':len(hub.clients),'simulator':dict(sim_state)}

@app.get('/ready')
def ready(): return {'ready':True}

@app.get('/api/nodes')
def nodes():
    with Session() as db: return [node_dict(x) for x in db.scalars(select(Node).order_by(Node.node_code))]

@app.get('/api/readings/{node_code}')
def readings(node_code:str,limit:int=20):
    limit=max(1,min(limit,500))
    with Session() as db:
        n=db.scalar(select(Node).where(Node.node_code==node_code))
        if not n: raise HTTPException(404,'Unknown node')
        rows=db.scalars(select(Reading).where(Reading.node_id==n.id).order_by(Reading.id.desc()).limit(limit)).all()
        return [{'timestamp':r.timestamp.isoformat(),'displacement_mm':r.displacement_mm,'risk_score':r.risk_score} for r in reversed(rows)]

def get_node(db, node_code: str) -> Node:
    n=db.scalar(select(Node).where(Node.node_code==node_code))
    if not n: raise HTTPException(404,'Unknown node')
    return n

def iso(v): return v.isoformat().replace('+00:00','Z') if v else None
def sector_dict(s:MineSector): return {'id':s.id,'mine_id':s.mine_id,'sector_code':s.sector_code,'name':s.name,'sector_type':s.sector_type,'level_name':s.level_name,'depth_m':s.depth_m,'risk_level':s.risk_level,'boundary_geojson':json.loads(s.boundary_geojson),'description':s.description,'created_at':iso(s.created_at),'updated_at':iso(s.updated_at)}
def landmark_dict(l:MineLandmark,sector:MineSector|None=None): return {'id':l.id,'mine_id':l.mine_id,'sector_id':l.sector_id,'sector_name':sector.name if sector else None,'level_name':sector.level_name if sector else None,'landmark_code':l.landmark_code,'name':l.name,'landmark_type':l.landmark_type,'latitude':l.latitude,'longitude':l.longitude,'local_x_m':l.local_x_m,'local_y_m':l.local_y_m,'local_z_m':l.local_z_m,'depth_m':l.depth_m,'description':l.description,'icon_type':l.icon_type,'enabled':l.enabled}
def placement_dict(db,n:Node):
    s=db.get(MineSector,n.sector_id) if n.sector_id else None;l=db.get(MineLandmark,n.nearest_landmark_id) if n.nearest_landmark_id else None;g=db.get(Gateway,n.gateway_id) if n.gateway_id else None;d=node_dict(n)
    d.update({'device_id':n.node_code,'sector_id':n.sector_id,'sector':sector_dict(s) if s else None,'nearest_landmark':landmark_dict(l,s) if l else None,'landmark_distance_m':n.landmark_distance_m,'landmark_bearing_deg':n.landmark_bearing_deg,'landmark_direction':bearing_name(n.landmark_bearing_deg),'installation_location_type':n.installation_location_type,'installation_depth_m':n.installation_depth_m,'mounting_height_m':n.mounting_height_m,'local_x_m':n.local_x_m,'local_y_m':n.local_y_m,'local_z_m':n.local_z_m,'position_accuracy_m':n.position_accuracy_m,'gateway':{'id':g.id,'gateway_code':g.gateway_code,'name':g.name,'latitude':g.latitude,'longitude':g.longitude,'status':g.status} if g else None,'configured_communication_range_m':n.configured_communication_range_m,'estimated_communication_range_m':n.estimated_communication_range_m,'coverage_status':n.coverage_status,'packet_loss_percent':round(max(0,min(100,(-n.rssi-75)*1.1+(0 if n.connection_status=='online' else 45))),1),'range_calibrated':False,'range_label':'Range not calibrated – demonstration estimate only','installation_notes':n.installation_notes,'last_location_verified_at':iso(n.last_location_verified_at)})
    return d
def bearing_name(v:float): return ['N','NE','E','SE','S','SW','W','NW'][round(v/45)%8]

def sector_coverage(db,s:MineSector):
    devices=list(db.scalars(select(Node).where(Node.sector_id==s.id))); geo=json.loads(s.boundary_geojson);ring=geo['coordinates'][0];minx,maxx=min(p[0] for p in ring),max(p[0] for p in ring);miny,maxy=min(p[1] for p in ring),max(p[1] for p in ring);covered=overlap=0;total=400
    for iy in range(20):
        lat=miny+(iy+.5)/20*(maxy-miny)
        for ix in range(20):
            lng=minx+(ix+.5)/20*(maxx-minx);hits=sum(math.hypot((lat-n.latitude)*111000,(lng-n.longitude)*102000)<=min(n.estimated_communication_range_m,220) for n in devices if n.connection_status!='offline')
            covered+=hits>0;overlap+=hits>1
    covered_pct=round(covered/total*100,1);overlap_pct=round(overlap/total*100,1)
    return {'sector_id':s.id,'sector_code':s.sector_code,'covered_percent':covered_pct,'overlap_percent':overlap_pct,'uncovered_percent':round(100-covered_pct,1),'covered_area_estimate_m2':round(covered_pct/100*abs((maxx-minx)*102000*(maxy-miny)*111000)),'overlap_area_estimate_m2':round(overlap_pct/100*abs((maxx-minx)*102000*(maxy-miny)*111000)),'device_count':len(devices),'weak_devices':sum(n.rssi<-105 for n in devices),'coverage_status':'active' if covered_pct>=65 else 'insufficient','suggested_placement':{'label':'Demonstration placement suggestion','local_x_percent':75,'local_y_percent':65,'disclaimer':'Not an operational mine-safety recommendation'}}

@app.get('/api/v1/mines/{mine_id}/module-summary')
def module_summary(mine_id:str):
    with Session() as db:
        ns=list(db.scalars(select(Node).order_by(Node.node_code))); alerts_count=len(list(db.scalars(select(Alert).where(Alert.status=='open'))))
        counts={k:sum(n.risk_class==k and n.connection_status!='offline' for n in ns) for k in ('safe','observation','warning','critical')}
        highest=max(ns,key=lambda n:n.risk_score) if ns else None
        return {'mine_id':mine_id,'mine_name':'MineGuard Demonstration Mine','total_modules':len(ns),'online_modules':sum(n.connection_status=='online' for n in ns),'offline_modules':sum(n.connection_status=='offline' for n in ns),**{f'{k}_modules':v for k,v in counts.items()},'active_alerts':alerts_count,'last_update':max((n.last_seen for n in ns if n.last_seen),default=None),'overall_risk':highest.risk_class if highest else 'safe','highest_risk_module':highest.node_code if highest else None,'modules':[node_dict(n) for n in ns]}

@app.get('/api/v1/mines/{mine_id}/regions')
def regions(mine_id:str):
    with Session() as db:
        ns=list(db.scalars(select(Node))); groups={}
        for n in ns:
            d=node_dict(n); groups.setdefault(d['region'],[]).append(d)
        return [{'id':name.lower().replace(' ','-'),'name':name,'module_count':len(items),'boundary':[[min(x['latitude'] for x in items)-.0003,min(x['longitude'] for x in items)-.0003],[max(x['latitude'] for x in items)+.0003,max(x['longitude'] for x in items)+.0003]]} for name,items in groups.items()]

@app.get('/api/v1/mines/{mine_id}/sectors')
def mine_sectors(mine_id:str):
    with Session() as db: return [sector_dict(s) for s in db.scalars(select(MineSector).where(MineSector.mine_id==mine_id).order_by(MineSector.sector_code))]

@app.get('/api/v1/sectors/{sector_id}')
def sector_detail(sector_id:int):
    with Session() as db:
        s=db.get(MineSector,sector_id)
        if not s: raise HTTPException(404,'Sector not found')
        devices=list(db.scalars(select(Node).where(Node.sector_id==s.id)));landmarks=list(db.scalars(select(MineLandmark).where(MineLandmark.sector_id==s.id)));result=sector_dict(s);result.update({'devices':len(devices),'online_devices':sum(n.connection_status=='online' for n in devices),'offline_devices':sum(n.connection_status=='offline' for n in devices),'landmarks':len(landmarks),'highest_risk_device':max(devices,key=lambda n:n.risk_score).node_code if devices else None,**sector_coverage(db,s)});return result

@app.get('/api/v1/sectors/{sector_id}/devices')
def sector_devices(sector_id:int):
    with Session() as db: return [placement_dict(db,n) for n in db.scalars(select(Node).where(Node.sector_id==sector_id).order_by(Node.node_code))]

@app.get('/api/v1/sectors/{sector_id}/coverage')
def coverage_for_sector(sector_id:int):
    with Session() as db:
        s=db.get(MineSector,sector_id)
        if not s: raise HTTPException(404,'Sector not found')
        return sector_coverage(db,s)

@app.get('/api/v1/mines/{mine_id}/landmarks')
def mine_landmarks(mine_id:str,page:int=1,page_size:int=100):
    with Session() as db:
        rows=list(db.scalars(select(MineLandmark).where(MineLandmark.mine_id==mine_id,MineLandmark.enabled==True).order_by(MineLandmark.landmark_code)));items=[landmark_dict(l,db.get(MineSector,l.sector_id)) for l in rows];start=(max(1,page)-1)*max(1,min(page_size,500));return {'items':items[start:start+page_size],'total':len(items),'page':page}

@app.get('/api/v1/landmarks/{landmark_id}')
def landmark_detail(landmark_id:int):
    with Session() as db:
        l=db.get(MineLandmark,landmark_id)
        if not l: raise HTTPException(404,'Landmark not found')
        result=landmark_dict(l,db.get(MineSector,l.sector_id));result['nearby_devices']=[{'device_id':n.node_code,'distance_m':n.landmark_distance_m,'bearing_deg':n.landmark_bearing_deg,'direction':bearing_name(n.landmark_bearing_deg)} for n in db.scalars(select(Node).where(Node.nearest_landmark_id==l.id))];return result

@app.get('/api/v1/devices/{device_id}/placement')
def device_placement(device_id:str):
    with Session() as db:return placement_dict(db,get_node(db,device_id))

@app.get('/api/v1/devices/{device_id}/coverage')
def device_coverage(device_id:str):
    with Session() as db:
        n=get_node(db,device_id);p=placement_dict(db,n);return {'device_id':device_id,'gateway':p['gateway'],'configured_range_m':n.configured_communication_range_m,'estimated_range_m':n.estimated_communication_range_m,'rssi':n.rssi,'snr':n.snr,'packet_loss_percent':p['packet_loss_percent'],'communication_quality':'weak' if n.rssi<-105 else ('fair' if n.rssi<-90 else 'good'),'last_packet':iso(n.last_seen),'calibrated':False,'label':'Estimated prototype communication coverage','disclaimer':'Range not calibrated – demonstration estimate only'}

@app.get('/api/v1/gateways')
def gateways():
    with Session() as db:return [{'id':g.id,'gateway_code':g.gateway_code,'name':g.name,'latitude':g.latitude,'longitude':g.longitude,'local_x_m':g.local_x_m,'local_y_m':g.local_y_m,'status':g.status,'configured_range_m':g.configured_range_m,'last_seen':iso(g.last_seen)} for g in db.scalars(select(Gateway))]

@app.get('/api/v1/gateways/{gateway_id}/coverage')
def gateway_coverage(gateway_id:int):
    with Session() as db:
        g=db.get(Gateway,gateway_id)
        if not g:raise HTTPException(404,'Gateway not found')
        devices=list(db.scalars(select(Node).where(Node.gateway_id==g.id)));return {'gateway_id':g.id,'gateway_code':g.gateway_code,'status':g.status,'connected_devices':[n.node_code for n in devices],'configured_range_m':g.configured_range_m,'label':'Estimated prototype communication coverage','calibrated':False}

@app.put('/api/v1/devices/{device_id}/placement')
def update_placement(device_id:str,p:PlacementUpdate,x_admin_token:str|None=Header(default=None)):
    expected=os.getenv('MINEGUARD_ADMIN_TOKEN')
    if not expected and APP_ENV=='production':raise HTTPException(503,'Administrative placement updates are not configured')
    if x_admin_token!=(expected or 'mineguard-demo-admin'):raise HTTPException(403,'Administrator authentication required')
    with Session() as db:
        n=get_node(db,device_id)
        if not db.get(MineSector,p.sector_id):raise HTTPException(422,'Unknown sector')
        landmark=db.get(MineLandmark,p.nearest_landmark_id)
        if not landmark or landmark.sector_id!=p.sector_id:raise HTTPException(422,'Landmark must belong to selected sector')
        if not db.get(Gateway,p.gateway_id):raise HTTPException(422,'Unknown gateway')
        for key,value in p.model_dump().items():setattr(n,key,value)
        n.last_location_verified_at=datetime.now(UTC);db.commit();return placement_dict(db,n)

@app.get('/api/v1/mines/{mine_id}/coverage-summary')
def coverage_summary(mine_id:str):
    with Session() as db:
        sectors=list(db.scalars(select(MineSector).where(MineSector.mine_id==mine_id)));landmarks=list(db.scalars(select(MineLandmark).where(MineLandmark.mine_id==mine_id,MineLandmark.enabled==True)));devices=list(db.scalars(select(Node)));gateways=list(db.scalars(select(Gateway)));coverage=[sector_coverage(db,s) for s in sectors];highest=max(sectors,key=lambda s:{'safe':0,'observation':1,'warning':2,'critical':3}.get(s.risk_level,0)) if sectors else None
        return {'mine':'MineGuard Demonstration Mine','total_sectors':len(sectors),'total_landmarks':len(landmarks),'total_devices':len(devices),'online_devices':sum(n.connection_status=='online' for n in devices),'offline_devices':sum(n.connection_status=='offline' for n in devices),'active_coverage_sectors':sum(c['coverage_status']=='active' for c in coverage),'insufficient_coverage_sectors':sum(c['coverage_status']=='insufficient' for c in coverage),'highest_risk_sector':highest.name if highest else None,'weak_lora_devices':sum(n.rssi<-105 for n in devices),'uncovered_area_percent':round(sum(c['uncovered_percent'] for c in coverage)/len(coverage),1) if coverage else 100,'coverage_overlap_percent':round(sum(c['overlap_percent'] for c in coverage)/len(coverage),1) if coverage else 0,'gateway_status':gateways[0].status if gateways else 'unavailable','last_update':iso(max((n.last_seen for n in devices if n.last_seen),default=datetime.now(UTC))),'coverage_disclaimer':'Coverage and range values are demonstration estimates for an educational prototype.'}

@app.get('/api/v1/regions/{region_id}/modules')
def region_modules(region_id:str):
    with Session() as db: return [d for d in (node_dict(n) for n in db.scalars(select(Node))) if d['region'].lower().replace(' ','-')==region_id]

@app.get('/api/v1/nodes/{node_code}/sensor-risk')
def node_sensor_risk(node_code:str):
    with Session() as db: return {'node_code':node_code,'policy':ANALYTICS_POLICY,'sensors':sensor_rows(get_node(db,node_code))}

@app.get('/api/v1/nodes/{node_code}/analytics')
def node_analytics(node_code:str):
    with Session() as db:
        n=get_node(db,node_code); d=node_dict(n); sensors=sensor_rows(n)
        contributors=sorted(({'sensor':s['sensor'],'score':s['risk_score'],'weight':ANALYTICS_POLICY['weights'].get(s['sensor'],.04)} for s in sensors),key=lambda x:x['score']*x['weight'],reverse=True)[:5]
        lead=contributors[0] if contributors else {'sensor':'none','score':0,'weight':0}; location=f"{d['region']}, {d['zone']}"
        d.update({'sensors':sensors,'contributing_factors':contributors,'risk_explanation':f"{d['risk_class'].title()} status at {node_code}, {location}. {SENSOR_CONFIG.get(lead['sensor'],{}).get('label','Sensor conditions')} contributes most to the {d['risk_score']:.0f}/100 ground-risk score. Predicted 24-hour displacement is {d['prediction']:.1f} mm with {d['confidence']:.0f}% confidence. Data source: {d['source_type'].upper()}."})
        return d

@app.get('/api/v1/nodes/{node_code}/sensor-variations')
def sensor_variations(node_code:str, limit:int=120):
    fields={'displacement_mm':'displacement_mm','movement_rate_mm_per_hour':'movement_rate','tilt_x_deg':'tilt_x','tilt_y_deg':'tilt_y','vibration_rms':'vibration','vibration_peak':'vibration_peak','soil_moisture_percent':'moisture','soil_pressure':'soil_pressure','rainfall_mm':'rainfall','temperature_c':'temperature','humidity_percent':'humidity','battery_percentage':'battery','battery_voltage':'battery_voltage','rssi':'rssi','snr':'snr','data_quality_score':'data_quality','risk_score':'risk_score'}
    with Session() as db:
        n=get_node(db,node_code); rows=list(reversed(db.scalars(select(Reading).where(Reading.node_id==n.id).order_by(Reading.id.desc()).limit(max(1,min(limit,1000)))).all()))
        return {'node_code':node_code,'series':{key:[{'timestamp':r.timestamp.isoformat(),'value':getattr(r,attr),'risk_status':r.risk_class} for r in rows] for key,attr in fields.items()},'thresholds':SENSOR_CONFIG}

@app.get('/api/v1/nodes/compare')
def compare(nodes:str=''):
    wanted={x.strip() for x in nodes.split(',') if x.strip()}
    with Session() as db: return [node_dict(n) for n in db.scalars(select(Node)) if not wanted or n.node_code in wanted]

@app.get('/api/v1/sensor-risk-matrix')
def sensor_risk_matrix(region:str|None=None,module:str|None=None,sensor:str|None=None,risk_level:str|None=None,source_type:str|None=None,page:int=1,page_size:int=100,format:str='json'):
    with Session() as db:
        rows=[]
        for n in db.scalars(select(Node).order_by(Node.node_code)):
            d=node_dict(n)
            for s in sensor_rows(n): rows.append({'module':n.node_code,'region':d['region'],'source_type':n.source_type,**s})
    rows=[r for r in rows if (not region or r['region']==region) and (not module or r['module']==module) and (not sensor or r['sensor']==sensor) and (not risk_level or r['risk_level'].lower()==risk_level.lower()) and (not source_type or r['source_type']==source_type)]
    if format=='csv':
        output=io.StringIO(); writer=csv.DictWriter(output,fieldnames=['module','region','sensor','label','value','unit','trend','change_1h','risk_score','risk_level','threshold','data_quality','anomaly_score','last_reading'],extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
        return StreamingResponse(iter([output.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=mineguard-sensor-risk.csv'})
    start=(max(1,page)-1)*max(1,min(page_size,500)); return {'items':rows[start:start+page_size],'total':len(rows),'page':page,'page_size':page_size}

@app.post('/api/telemetry')
async def telemetry(t:Telemetry): return await ingest(t)

@app.get('/api/alerts')
def alerts(limit:int=50):
    with Session() as db:
        rows=db.scalars(select(Alert).order_by(Alert.id.desc()).limit(max(1,min(limit,200)))).all()
        return [{'id':a.id,'node_code':a.node_code,'severity':a.severity,'title':a.title,'message':a.message,'category':a.category,'status':a.status,'created_at':a.created_at.isoformat()} for a in rows]

@app.post('/api/alerts/{alert_id}/acknowledge')
def acknowledge(alert_id:int):
    with Session() as db:
        a=db.get(Alert,alert_id)
        if not a: raise HTTPException(404,'Alert not found')
        a.status='acknowledged'; a.acknowledged_at=datetime.now(UTC); db.commit(); return {'ok':True}

@app.get('/api/public/status')
def public_status():
    with Session() as db:
        ns=list(db.scalars(select(Node))); online=[n for n in ns if n.connection_status=='online']; highest=max(ns,key=lambda n:n.risk_score) if ns else None
        return {'mine':'MineGuard Demonstration Mine','overall_risk':highest.risk_class if highest else 'unknown','risk_score':highest.risk_score if highest else 0,'online_nodes':len(online),'total_nodes':len(ns),'last_update':max((n.last_seen for n in ns if n.last_seen),default=None),'disclaimer':'Prototype demonstration data; not an operational mine-safety determination.'}

@app.post('/api/simulator/start')
async def start_sim(command:SimCommand):
    global sim_task
    sim_state.update(command.model_dump()); sim_state['running']=True
    if not sim_task or sim_task.done(): sim_task=asyncio.create_task(simulator_loop())
    return sim_state

@app.post('/api/simulator/pause')
def pause(): sim_state['running']=False; return sim_state

@app.post('/api/simulator/reset')
async def reset():
    sim_state.update({'running':False,'scenario':'normal'})
    with Session() as db:
        for n in db.scalars(select(Node)): n.displacement_mm=0;n.risk_score=10;n.risk_class='safe';n.connection_status='online';n.sensor_health='normal';n.data_quality=100
        db.commit()
    return {'ok':True}

@app.websocket('/ws/live')
async def live(ws:WebSocket):
    await hub.connect(ws)
    try:
        await ws.send_json({'type':'hello','message_sequence':hub.seq})
        while True:
            try: await asyncio.wait_for(ws.receive_text(),timeout=20)
            except asyncio.TimeoutError: await ws.send_json({'type':'heartbeat','message_sequence':hub.seq})
    except WebSocketDisconnect: pass
    finally: hub.remove(ws)


# Render builds the Vite application into frontend/dist. Serving it from the
# API keeps the UI, REST endpoints, and WebSocket on one production origin.
FRONTEND_DIST = ROOT.parent / 'frontend' / 'dist'

@app.get('/{full_path:path}', include_in_schema=False)
def frontend(full_path: str):
    if not FRONTEND_DIST.is_dir():
        raise HTTPException(404, 'Frontend build is not available')
    requested = (FRONTEND_DIST / full_path).resolve()
    if requested.is_relative_to(FRONTEND_DIST.resolve()) and requested.is_file():
        return FileResponse(requested)
    return FileResponse(FRONTEND_DIST / 'index.html')
