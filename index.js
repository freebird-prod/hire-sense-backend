import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { Resend } from 'resend';

dotenv.config();
const app = express();
const PORT = process.env.PORT || 5000;

const resend = new Resend(process.env.RESEND_API_KEY);


app.use(cors());
app.use(express.json());

app.post('/api/send-email', async (req, res) => {
  const { name, email, role, skills } = req.body;

  if (!name || !email || !role || !Array.isArray(skills)) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  const text = `Dear ${name},

We reviewed your profile and were impressed with your qualifications.
Based on your skills (${skills.join(', ')}), you are a great fit for the role of "${role}".

We’d love to move forward. Please reply if interested.

Regards,
HireSense AI`;

  try {
    const { data, error } = await resend.emails.send({
      from: 'onboarding@resend.dev',
      to: ['techpro03dharun@gmail.com'],
      subject: `Opportunity: ${role}`,
      text,
    });

    if (error) {
      console.error('Resend error:', error);
      return res.status(500).json({ error: 'Failed to send email' });
    }

    res.status(200).json({ success: true, id: data?.id });
  } catch (err) {
    console.error('Server error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

app.listen(PORT, () => console.log(`Server listening on http://localhost:${PORT}`));
