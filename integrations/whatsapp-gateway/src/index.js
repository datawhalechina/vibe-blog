/**
 * vibe-blog WhatsApp Gateway
 *
 * 轻量级 WhatsApp 网关，直接将消息路由到 vibe-blog 对话式写作 API。
 * 不依赖 NanoClaw，不需要 Container/Agent/IPC。
 *
 * 架构：WhatsApp ←→ Gateway ←→ vibe-blog /api/chat/*
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import makeWASocket, {
  DisconnectReason,
  makeCacheableSignalKeyStore,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import qrcode from 'qrcode-terminal';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_DIR = path.resolve(__dirname, '..', 'store', 'auth');
const SESSIONS_FILE = path.resolve(__dirname, '..', 'store', 'sessions.json');

const VIBE_BLOG_URL = process.env.VIBE_BLOG_URL || 'http://localhost:5001';
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';

const logger = pino({
  level: LOG_LEVEL,
  transport: { target: 'pino-pretty', options: { colorize: true } },
});

// ========== 会话管理 ==========

// chatJid → { sessionId, topic, status }
let chatSessions = {};

function loadSessions() {
  try {
    if (fs.existsSync(SESSIONS_FILE)) {
      chatSessions = JSON.parse(fs.readFileSync(SESSIONS_FILE, 'utf-8'));
      logger.info({ count: Object.keys(chatSessions).length }, '已加载会话映射');
    }
  } catch (err) {
    logger.warn({ err }, '加载会话映射失败，使用空映射');
    chatSessions = {};
  }
}

function saveSessions() {
  fs.mkdirSync(path.dirname(SESSIONS_FILE), { recursive: true });
  fs.writeFileSync(SESSIONS_FILE, JSON.stringify(chatSessions, null, 2));
}

// ========== vibe-blog API 调用 ==========

async function callApi(method, apiPath, userId, body) {
  const url = `${VIBE_BLOG_URL}${apiPath}`;
  const headers = { 'Content-Type': 'application/json' };
  if (userId) headers['X-User-Id'] = userId;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const resp = await fetch(url, opts);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${resp.status}: ${text}`);
  }
  return resp.json();
}

// ========== 意图识别 & 消息路由 ==========

/**
 * 解析用户消息意图，映射到对话式写作 API 操作。
 *
 * 支持的指令：
 *   写 <主题>          → 创建会话 + 一键生成
 *   新话题 <主题>      → 创建新会话
 *   搜索 / 调研        → 调研
 *   大纲              → 生成大纲
 *   写作 / 开始写      → 一键生成
 *   预览              → 预览当前文章
 *   发布              → 发布
 *   状态              → 查看当前会话状态
 *   帮助              → 显示帮助
 */
function parseIntent(text) {
  const t = text.trim();

  // 写 <主题> — 一键生成
  const writeMatch = t.match(/^写[写作]?\s+(.+)/);
  if (writeMatch) return { action: 'write_full', topic: writeMatch[1].trim() };

  // 新话题 <主题>
  const newMatch = t.match(/^(新话题|新主题|new)\s+(.+)/i);
  if (newMatch) return { action: 'create', topic: newMatch[2].trim() };

  // 搜索/调研
  if (/^(搜索|调研|research|search)/i.test(t)) return { action: 'search' };

  // 大纲
  if (/^(大纲|outline)/i.test(t)) return { action: 'outline' };

  // 写作/开始写/生成
  if (/^(写作|开始写|生成|generate|write)/i.test(t)) return { action: 'generate' };

  // 预览
  if (/^(预览|preview)/i.test(t)) return { action: 'preview' };

  // 发布
  if (/^(发布|publish)/i.test(t)) return { action: 'publish' };

  // 状态
  if (/^(状态|status)/i.test(t)) return { action: 'status' };

  // 帮助
  if (/^(帮助|help|\/help|\?)/i.test(t)) return { action: 'help' };

  // 列出会话
  if (/^(列表|list|我的文章)/i.test(t)) return { action: 'list' };

  // 默认：如果有活跃会话，当作自由对话；否则当作新主题
  return { action: 'auto', text: t };
}

const HELP_TEXT = `📝 *vibe-blog 对话式写作*

指令：
• *写 <主题>* — 一键生成完整博客
• *新话题 <主题>* — 创建写作会话
• *搜索* — 调研当前主题
• *大纲* — 生成文章大纲
• *写作* — 开始写作
• *预览* — 预览文章
• *发布* — 发布文章
• *状态* — 查看当前进度
• *列表* — 查看所有文章
• *帮助* — 显示此帮助

直接发送主题也可以开始写作！`;

async function handleMessage(chatJid, text, sendReply) {
  const userId = chatJid;
  const intent = parseIntent(text);
  const session = chatSessions[chatJid];

  try {
    switch (intent.action) {
      case 'help':
        await sendReply(HELP_TEXT);
        return;

      case 'list': {
        const sessions = await callApi('GET', '/api/chat/sessions', userId);
        if (!sessions.length) {
          await sendReply('📭 还没有写作会话。发送 "写 <主题>" 开始创作！');
          return;
        }
        const lines = sessions.map(
          (s, i) => `${i + 1}. *${s.topic}* (${s.status})`
        );
        await sendReply(`📋 你的写作会话：\n\n${lines.join('\n')}`);
        return;
      }

      case 'status': {
        if (!session) {
          await sendReply('没有活跃的写作会话。发送 "写 <主题>" 开始创作！');
          return;
        }
        const detail = await callApi(
          'GET',
          `/api/chat/session/${session.sessionId}`,
          userId
        );
        const sectionCount = detail.sections?.length || 0;
        const wordCount = (detail.sections || []).reduce(
          (sum, s) => sum + (s.content?.length || 0),
          0
        );
        await sendReply(
          `📊 当前会话：*${detail.topic}*\n` +
            `状态：${detail.status}\n` +
            `章节：${sectionCount}\n` +
            `字数：~${wordCount}`
        );
        return;
      }

      case 'write_full':
      case 'create': {
        const topic = intent.topic;
        await sendReply(`🚀 开始写作：*${topic}*\n请稍候...`);

        const created = await callApi('POST', '/api/chat/session', userId, {
          topic,
          article_type: 'problem-solution',
          target_audience: 'beginner',
          target_length: 'medium',
        });

        chatSessions[chatJid] = {
          sessionId: created.session_id,
          topic,
          status: 'created',
        };
        saveSessions();

        if (intent.action === 'create') {
          await sendReply(
            `✅ 会话已创建！\n` +
              `ID: ${created.session_id}\n\n` +
              `接下来可以发送：\n• *搜索* — 调研主题\n• *大纲* — 生成大纲\n• *写作* — 一键生成`
          );
          return;
        }

        // write_full: 触发一键生成
        await sendReply('🔍 正在调研...');
        const genResult = await callApi(
          'POST',
          `/api/chat/session/${created.session_id}/generate`,
          userId
        );

        chatSessions[chatJid].status = 'generating';
        chatSessions[chatJid].taskId = genResult.task_id;
        saveSessions();

        await sendReply(
          `⏳ 一键生成已启动！\n` +
            `任务 ID: ${genResult.task_id}\n\n` +
            `生成过程需要几分钟，完成后会通知你。\n` +
            `发送 *状态* 查看进度。`
        );
        return;
      }

      case 'search': {
        if (!session) {
          await sendReply('❌ 没有活跃会话。先发送 "新话题 <主题>" 创建一个。');
          return;
        }
        await sendReply('🔍 正在调研...');
        const result = await callApi(
          'POST',
          `/api/chat/session/${session.sessionId}/search`,
          userId
        );
        const count = result.search_results?.length || 0;
        await sendReply(`✅ 调研完成，找到 ${count} 条相关资料。\n发送 *大纲* 继续。`);
        chatSessions[chatJid].status = 'researched';
        saveSessions();
        return;
      }

      case 'outline': {
        if (!session) {
          await sendReply('❌ 没有活跃会话。先发送 "新话题 <主题>" 创建一个。');
          return;
        }
        await sendReply('📋 正在生成大纲...');
        const result = await callApi(
          'POST',
          `/api/chat/session/${session.sessionId}/outline`,
          userId
        );
        const outline = result.outline;
        if (outline) {
          const sections = (outline.sections || [])
            .map((s, i) => `${i + 1}. ${s.title}`)
            .join('\n');
          await sendReply(
            `📋 大纲：*${outline.title || session.topic}*\n\n${sections}\n\n发送 *写作* 开始写作。`
          );
          chatSessions[chatJid].status = 'outlined';
          saveSessions();
        } else {
          await sendReply('⚠️ 大纲生成失败，请重试。');
        }
        return;
      }

      case 'generate': {
        if (!session) {
          await sendReply('❌ 没有活跃会话。先发送 "新话题 <主题>" 创建一个。');
          return;
        }
        await sendReply('✍️ 开始一键生成...');
        const result = await callApi(
          'POST',
          `/api/chat/session/${session.sessionId}/generate`,
          userId
        );
        chatSessions[chatJid].status = 'generating';
        chatSessions[chatJid].taskId = result.task_id;
        saveSessions();
        await sendReply(
          `⏳ 生成中...\n任务 ID: ${result.task_id}\n发送 *状态* 查看进度。`
        );
        return;
      }

      case 'preview': {
        if (!session) {
          await sendReply('❌ 没有活跃会话。');
          return;
        }
        const result = await callApi(
          'GET',
          `/api/chat/session/${session.sessionId}/preview`,
          userId
        );
        const preview = result.markdown || result.content || '(暂无内容)';
        // WhatsApp 消息限制，截断到 4000 字符
        const truncated =
          preview.length > 4000
            ? preview.substring(0, 4000) + '\n\n...(已截断)'
            : preview;
        await sendReply(`📖 预览：\n\n${truncated}`);
        return;
      }

      case 'publish': {
        if (!session) {
          await sendReply('❌ 没有活跃会话。');
          return;
        }
        await callApi(
          'POST',
          `/api/chat/session/${session.sessionId}/publish`,
          userId
        );
        await sendReply(`✅ 文章已发布！\n主题：*${session.topic}*`);
        chatSessions[chatJid].status = 'completed';
        saveSessions();
        return;
      }

      case 'auto': {
        // 没有匹配到指令：如果没有活跃会话，当作新主题
        if (!session) {
          // 当作 write_full
          const topic = intent.text;
          await sendReply(`🚀 开始写作：*${topic}*\n请稍候...`);

          const created = await callApi('POST', '/api/chat/session', userId, {
            topic,
          });

          chatSessions[chatJid] = {
            sessionId: created.session_id,
            topic,
            status: 'created',
          };
          saveSessions();

          const genResult = await callApi(
            'POST',
            `/api/chat/session/${created.session_id}/generate`,
            userId
          );

          chatSessions[chatJid].status = 'generating';
          chatSessions[chatJid].taskId = genResult.task_id;
          saveSessions();

          await sendReply(
            `⏳ 一键生成已启动！\n任务 ID: ${genResult.task_id}\n发送 *状态* 查看进度。`
          );
        } else {
          await sendReply(
            `当前会话：*${session.topic}* (${session.status})\n\n` +
              `发送 *帮助* 查看可用指令。`
          );
        }
        return;
      }
    }
  } catch (err) {
    logger.error({ chatJid, intent, err: err.message }, '处理消息失败');
    await sendReply(`❌ 操作失败：${err.message}`);
  }
}

// ========== WhatsApp 连接 ==========

let sock;
let needsAuth = false;   // 是否收到过 QR 码（说明未认证）
let reconnectCount = 0;
const MAX_RECONNECT = 5;

async function connectWhatsApp() {
  fs.mkdirSync(AUTH_DIR, { recursive: true });

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  // 检查是否已有认证凭据
  if (!state.creds.registered) {
    logger.error('❌ WhatsApp 未认证！请先运行: node src/auth.js');
    logger.info('认证步骤：');
    logger.info('  1. cd integrations/whatsapp-gateway');
    logger.info('  2. node src/auth.js');
    logger.info('  3. 用手机 WhatsApp 扫描二维码');
    process.exit(1);
  }

  const waLogger = pino({ level: 'warn' });

  sock = makeWASocket({
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, waLogger),
    },
    printQRInTerminal: false,
    logger: waLogger,
    browser: ['VibeBlog', 'Chrome', '1.0.0'],
  });

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      // 收到 QR 码说明凭据已失效
      needsAuth = true;
      logger.error('❌ WhatsApp 凭据已失效，请重新认证: node src/auth.js');
      process.exit(1);
    }

    if (connection === 'close') {
      const reason = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect =
        reason !== DisconnectReason.loggedOut && !needsAuth;
      logger.info({ reason, shouldReconnect, reconnectCount }, '连接关闭');

      if (shouldReconnect && reconnectCount < MAX_RECONNECT) {
        reconnectCount++;
        const delay = Math.min(3000 * reconnectCount, 30000);
        logger.info({ delay: `${delay}ms` }, `正在重连 (${reconnectCount}/${MAX_RECONNECT})...`);
        setTimeout(connectWhatsApp, delay);
      } else if (reconnectCount >= MAX_RECONNECT) {
        logger.error(`重连 ${MAX_RECONNECT} 次仍失败，退出。`);
        process.exit(1);
      } else {
        logger.info('已登出。请运行 node src/auth.js 重新认证。');
        process.exit(0);
      }
    } else if (connection === 'open') {
      reconnectCount = 0; // 连接成功，重置计数
      logger.info('✓ WhatsApp 已连接');
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message) continue;
      if (msg.key.fromMe) continue; // 忽略自己发的消息

      const chatJid = msg.key.remoteJid;
      if (!chatJid || chatJid === 'status@broadcast') continue;

      // 提取文本内容
      const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        '';
      if (!text.trim()) continue;

      logger.info(
        { chatJid, sender: msg.pushName, text: text.substring(0, 100) },
        '收到消息'
      );

      const sendReply = async (replyText) => {
        try {
          await sock.sendMessage(chatJid, { text: replyText });
        } catch (err) {
          logger.error({ chatJid, err: err.message }, '发送回复失败');
        }
      };

      await handleMessage(chatJid, text, sendReply);
    }
  });
}

// ========== 启动 ==========

async function main() {
  logger.info({ vibeBlogUrl: VIBE_BLOG_URL }, 'vibe-blog WhatsApp Gateway 启动');
  loadSessions();
  await connectWhatsApp();
}

main().catch((err) => {
  logger.error({ err }, '启动失败');
  process.exit(1);
});
