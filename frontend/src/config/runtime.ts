const developmentApi='http://127.0.0.1:8000';
export const API_BASE_URL=(import.meta.env.VITE_API_BASE_URL||import.meta.env.VITE_API_URL||(import.meta.env.DEV?developmentApi:'')).replace(/\/$/,'');
export const WS_URL=import.meta.env.VITE_WS_URL||(import.meta.env.DEV?'ws://127.0.0.1:8000/ws/live':`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/live`);
export const productionApiConfigured=Boolean(API_BASE_URL);
