import test from "node:test";
import assert from "node:assert/strict";
import { createApp, CONTACT_TO } from "../server.js";

function buildResponse() {
  return {
    statusCode: 200,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
    sendFile(_filePath) {
      return this;
    },
  };
}

function buildRequest(body = {}) {
  return { body };
}

function findRouteHandler(app, method, path) {
  const layer = app._router.stack.find(
    (entry) => entry.route && entry.route.path === path && entry.route.methods[method]
  );

  if (!layer) {
    throw new Error(`Route ${method.toUpperCase()} ${path} not found`);
  }

  return layer.route.stack[0].handle;
}

test("/api/contact sends email to hardcoded address", async () => {
  let sentOptions;
  const transporter = {
    async sendMail(options) {
      sentOptions = options;
    },
  };

  process.env.EMAIL_USER = "sender@example.com";

  const app = createApp({ transporter });
  const handler = findRouteHandler(app, "post", "/api/contact");
  const req = buildRequest({
    name: "Ada",
    email: "ada@example.com",
    message: "Hello",
  });
  const res = buildResponse();

  await handler(req, res);

  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body, { ok: true });
  assert.equal(sentOptions.to, CONTACT_TO);
});

test("/api/contact does not send email for honeypot submissions", async () => {
  let sendCount = 0;
  const transporter = {
    async sendMail() {
      sendCount += 1;
    },
  };

  const app = createApp({ transporter });
  const handler = findRouteHandler(app, "post", "/api/contact");
  const req = buildRequest({
    name: "Ada",
    email: "ada@example.com",
    message: "Hello",
    company: "Robots Inc",
  });
  const res = buildResponse();

  await handler(req, res);

  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body, { ok: true });
  assert.equal(sendCount, 0);
});
