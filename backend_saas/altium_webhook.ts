// backend_saas/altium_webhook.ts
import express from 'express';
import axios from 'axios';

const app = express();
app.use(express.json());

const ALTIUM_API_URL = process.env.ALTIUM_API_URL || 'https://api.altium.com/v1';
const ALTIUM_API_KEY = process.env.ALTIUM_API_KEY || 'default_key';

app.post('/webhook/handover-approved', async (req, res) => {
    try {
        const handoverData = req.body;

        // Verifying minimum coherence for PCB generation
        if (handoverData.coherence < 0.95) {
             return res.status(400).json({ error: "Coherence too low for auto-generation" });
        }

        console.log(`Received approved handover ${handoverData.id}. Initiating Altium PCB generation...`);

        // Payload for Altium MCP API
        const altiumPayload = {
            projectName: `Project_${handoverData.projectId}`,
            designData: handoverData.gamma_b, // Using the genomic phase data for the layout
            parameters: handoverData.metadata
        };

        // Call Altium API
        const altiumResponse = await axios.post(`${ALTIUM_API_URL}/pcb/generate`, altiumPayload, {
            headers: {
                'Authorization': `Bearer ${ALTIUM_API_KEY}`,
                'Content-Type': 'application/json'
            }
        });

        console.log(`Altium PCB generation initiated. Job ID: ${altiumResponse.data.jobId}`);

        res.status(200).json({ status: "success", jobId: altiumResponse.data.jobId });

    } catch (error: any) {
        console.error("Error processing webhook or contacting Altium:", error.message);
        res.status(500).json({ error: "Internal Server Error" });
    }
});

const port = process.env.PORT || 3001;
app.listen(port, () => {
    console.log(`Altium Webhook Service listening on port ${port}`);
});