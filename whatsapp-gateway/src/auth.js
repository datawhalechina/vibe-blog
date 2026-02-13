/**
 * WhatsApp 认证脚本
 * 显示 QR 码，等待扫描，保存凭据后退出。
 *
 * Usage: node src/auth.js
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import qrcode from 'qrcode-terminal';
import makeWASocket, {
  DisconnectReason,
  makeCacheableSignalKeyStore,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';
import pino from 'pino';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_DIR = path.resolve(__dirname, '..', 'store', 'auth');

const logger = pino({ level: 'warn' });

async function authenticate() {
  fs.mkdirSync(AUTH_DIR, { recursive: true });

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  if (state.creds.registered) {
    console.log('✓ 已通过 WhatsApp 认证');
    console.log('  如需重新认证，删除 store/auth 目录后重新运行。');
    process.exit(0);
  }

  console.log('开始 WhatsApp 认证...\n');

  const sock = makeWASocket({
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    printQRInTerminal: false,
    logger,
    browser: ['VibeBlog', 'Chrome', '1.0.0'],
  });

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('用 WhatsApp 扫描下方二维码:\n');
      console.log('  1. 打开手机 WhatsApp');
      console.log('  2. 设置 → 已关联设备 → 关联新设备');
      console.log('  3. 将摄像头对准下方二维码\n');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'close') {
      const reason = lastDisconnect?.error?.output?.statusCode;
      if (reason === DisconnectReason.loggedOut) {
        console.log('\n✗ 已登出。删除 store/auth 后重试。');
      } else {
        console.log('\n✗ 连接失败，请重试。');
      }
      process.exit(1);
    }

    if (connection === 'open') {
      console.log('\n✓ WhatsApp 认证成功！');
      console.log('  凭据已保存到 store/auth/');
      console.log('  现在可以启动 WhatsApp 网关了。\n');
      setTimeout(() => process.exit(0), 1000);
    }
  });

  sock.ev.on('creds.update', saveCreds);
}

authenticate().catch((err) => {
  console.error('认证失败:', err.message);
  process.exit(1);
});
