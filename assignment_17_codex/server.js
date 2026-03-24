import express from "express";
import nodemailer from "nodemailer";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";

dotenv.config();

const port = process.env.PORT || 3000;
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const CONTACT_TO = "22dsyndergaard@gmail.com";

export function buildTransporter() {
  const emailUser = process.env.EMAIL_USER;
  const emailPass = process.env.EMAIL_APP_PASSWORD?.replace(/\s+/g, "");

  if (!emailUser || !emailPass) {
    console.warn("Missing EMAIL_USER or EMAIL_APP_PASSWORD in environment.");
  }

  return nodemailer.createTransport({
    host: "smtp.gmail.com",
    port: 465,
    secure: true,
    auth: {
      user: emailUser,
      pass: emailPass,
    },
  });
}

export function createApp({ transporter = buildTransporter() } = {}) {
  const app = express();

  app.use(express.json({ limit: "25kb" }));
  app.use(express.static(__dirname));

  app.post("/api/contact", async (req, res) => {
    const { name, email, message, company } = req.body || {};

    if (company) {
      return res.status(200).json({ ok: true });
    }

    if (!name || !email || !message) {
      return res.status(400).json({ error: "Name, email, and message are required." });
    }

    try {
      await transporter.sendMail({
        from: `"Course Contact" <${process.env.EMAIL_USER}>`,
        to: CONTACT_TO,
        replyTo: email,
        subject: `New course message from ${name}`,
        text: `Name: ${name}\nEmail: ${email}\n\n${message}`,
      });
      return res.status(200).json({ ok: true });
    } catch (error) {
      console.error("Email send failed:", error);
      return res.status(500).json({ error: "Email failed to send." });
    }
  });

  app.get("*", (_req, res) => {
    res.sendFile(path.join(__dirname, "index.html"));
  });

  return app;
}

if (process.argv[1] === __filename) {
  const app = createApp();
  app.listen(port, () => {
    console.log(`Server listening on http://localhost:${port}`);
  });
}
