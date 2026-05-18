const WebSocket = require('ws');

const WSS_URL = 'wss://bug-free-space-dollop-6j657j6p97v24vxw-18789.app.github.dev';
const TOKEN = 'f37862a2f129519379d3bbcaee0ade18681194892b67c9c0';

// 构造带令牌的 WebSocket URL
const url = `${WSS_URL}?token=${TOKEN}`;

console.log(`Connecting to ${url} ...`);

const ws = new WebSocket(url);

ws.on('open', function open() {
  console.log('✅ Connected successfully!');
  // 可以发送一个简单的心跳或查询消息（根据 OpenClaw 协议）
  ws.send(JSON.stringify({ type: 'ping' }));
  // 保持连接几秒后退出
  setTimeout(() => {
    ws.close();
    process.exit(0);
  }, 5000);
});

ws.on('message', function incoming(data) {
  console.log('📩 Received:', data.toString());
});

ws.on('error', function error(err) {
  console.error('❌ WebSocket error:', err.message);
  process.exit(1);
});

ws.on('close', function close(code, reason) {
  console.log(`🔒 Connection closed: ${code} - ${reason}`);
  process.exit(0);
});
