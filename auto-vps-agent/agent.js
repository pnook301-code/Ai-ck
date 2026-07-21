const { PlaywrightCrawler } = require('crawlee');
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// Load config
const config = JSON.parse(fs.readFileSync('/root/.ck-nexus/config.json', 'utf8'));
const GROQ_KEY = config.groq?.key || config.GROQ_API_KEY || '';
const OPENROUTER_KEY = config.openrouter?.key || config.OPENROUTER_API_KEY || '';
const SD_PATH = '/workspace/ck-nexus';

// VPS Providers that offer free tiers
const FREE_VPS_PROVIDERS = [
    {
        name: 'Oracle Cloud',
        url: 'https://cloud.oracle.com',
        type: 'always-free',
        specs: '4 OCPU/24GB RAM',
        days: 365
    },
    {
        name: 'GratisVPS',
        url: 'https://gratisvps.net/cvps',
        type: 'free',
        specs: '2GB RAM/2 CPU',
        days: -1
    },
    {
        name: 'SolusVM',
        url: 'https://www.solusvm.com/free-trial',
        type: 'trial',
        specs: 'Sandbox',
        days: 30
    },
    {
        name: 'Google Cloud',
        url: 'https://console.cloud.google.com/billing/free',
        type: 'free-tier',
        specs: '$300 credit/e2-micro',
        days: 90
    }
];

// AI Analysis using Groq
async function analyzeWithAI(text) {
    try {
        const prompt = `คุณคือ AI นักวิเคราะห์ระบบคลาวด์และ VPS ฟรี
วิเคราะห์ข้อความนี้: "${text}"

ตอบกลับเป็น JSON เท่านั้น:
{
  "isFreeVPS": true/false,
  "trustScore": 1-10,
  "reason": "เหตุผลสั้นๆ ภาษาไทย",
  "recommended": true/false
}`;

        const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${GROQ_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'llama-3.3-70b-versatile',
                messages: [{ role: 'user', content: prompt }],
                max_tokens: 500,
                temperature: 0.3
            })
        });

        if (response.ok) {
            const data = await response.json();
            const content = data.choices[0].message.content;
            const jsonMatch = content.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
        }
    } catch (e) {
        console.log(`⚠️ AI analysis error: ${e.message}`);
    }
    return { isFreeVPS: false, trustScore: 0, reason: 'AI analysis failed', recommended: false };
}

// Save VPS to database
function saveVPSToDB(provider, ip, password) {
    const dbPath = path.join(SD_PATH, 'nexus_system_sd.db');
    const sqlite3 = require('sqlite3').verbose();
    const db = new sqlite3.Database(dbPath);

    db.run(`UPDATE autonomous_vps_servers 
            SET vps_ip=?, vps_password=?, status='ACTIVE', 
                notes=?, timestamp=datetime('now')
            WHERE provider_name LIKE ?`,
        [ip, password, `SSH_IP:${ip}|SSH_PASSWORD:${password}`, `%${provider}%`],
        function(err) {
            if (err) console.log(`⚠️ DB error: ${err.message}`);
            else console.log(`💾 Saved ${provider} to database`);
            db.close();
        }
    );
}

// Main crawler
const crawler = new PlaywrightCrawler({
    launchContext: {
        launchOptions: {
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        }
    },
    maxRequestsPerCrawl: 20,
    navigationTimeoutSecs: 30,

    async requestHandler({ page, request, log }) {
        log.info(`🔍 Checking: ${request.url}`);

        try {
            await page.waitForLoadState('domcontentloaded', { timeout: 15000 });

            // Analyze page content
            const pageText = await page.textContent('body');
            const analysis = await analyzeWithAI(pageText.substring(0, 2000));

            if (analysis.isFreeVPS && analysis.trustScore >= 7) {
                log.info(`✅ AI Approved: ${analysis.reason} (Score: ${analysis.trustScore})`);

                // Take screenshot
                const screenshotPath = path.join(SD_PATH, `vps_${Date.now()}.png`);
                await page.screenshot({ path: screenshotPath, fullPage: false });
                log.info(`📸 Screenshot saved: ${screenshotPath}`);

                // Try to find signup button
                const signupBtn = await page.$('a[href*="signup"], a[href*="register"], a[href*="create"], button:has-text("Sign Up"), button:has-text("Register"), button:has-text("Create")');
                if (signupBtn) {
                    log.info(`🚀 Found signup button, clicking...`);
                    await signupBtn.click();
                    await page.waitForLoadState('domcontentloaded', { timeout: 15000 });

                    // Capture form fields
                    const formFields = await page.$$eval('input[type="email"], input[type="text"], input[type="password"]', inputs =>
                        inputs.map(i => ({ type: i.type, name: i.name || i.id, placeholder: i.placeholder }))
                    );
                    log.info(`📝 Found ${formFields.length} form fields: ${JSON.stringify(formFields)}`);

                    // Save form structure
                    fs.writeFileSync(path.join(SD_PATH, `vps_form_${Date.now()}.json`), JSON.stringify({
                        url: request.url,
                        fields: formFields,
                        screenshot: screenshotPath,
                        analysis: analysis
                    }, null, 2));
                }
            } else {
                log.info(`❌ AI Rejected: ${analysis.reason}`);
            }
        } catch (e) {
            log.info(`⚠️ Error processing page: ${e.message}`);
        }
    }
});

// Start the agent
async function main() {
    console.log('╔══════════════════════════════════════════════╗');
    console.log('║  🤖 CK-NEXUS AUTO-VPS AGENT ENGINE          ║');
    console.log('╠══════════════════════════════════════════════╣');
    console.log('║  🧠 AI: Groq Llama 3.3 70B                  ║');
    console.log('║  🕵️ Bot: Crawlee + Playwright                ║');
    console.log('║  🎯 Target: Free VPS Providers               ║');
    console.log('╚══════════════════════════════════════════════╝');
    console.log('');

    // Scan free VPS sources
    const startUrls = [
        'https://gratisvps.net/cvps',
        'https://www.solusvm.com/free-trial',
        'https://lowendtalk.com'
    ];

    console.log(`🎯 Scanning ${startUrls.length} sources for free VPS...`);

    try {
        await crawler.run(startUrls);
    } catch (e) {
        console.log(`⚠️ Crawler stopped: ${e.message}`);
    }

    console.log('\n✅ Scan complete! Check screenshots in', SD_PATH);
}

main().catch(console.error);
