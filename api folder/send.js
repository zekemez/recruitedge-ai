import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

export default async function handler(req, res) {
  try {
    const data = await resend.emails.send({
      from: "Isaac <isaac@recruitedge.site>",
      to: ["isaacmesnekoff@gmail.com"],
      subject: "RecruitEdge test email",
      text: "Your RecruitEdge email system is working ✅",
    });

    res.status(200).json({ success: true, data });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
