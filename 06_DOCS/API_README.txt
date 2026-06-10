API ENDPOINTS

POST /api/points/add

{
  "api_secret": "YOUR_SECRET",
  "steam64": "7656119...",
  "points": 1,
  "reason": "normal_zombie_kill",
  "reference": "server1"
}

POST /api/orders/pending

{
  "api_secret": "YOUR_SECRET",
  "server_key": "server1"
}

POST /api/orders/mark-delivered

{
  "api_secret": "YOUR_SECRET",
  "order_id": 1,
  "message": "written to queue"
}
