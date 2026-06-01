require('dotenv').config({ path: '.env.local' });
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;

app.use(express.json());
app.use(express.static(__dirname));

// ── 候选人画像 System Prompt ──────────────────────────────────────────────────
const SYSTEM_PROMPT = `你是一位专业的HR招聘顾问，擅长评估候选人与岗位的匹配度。

候选人画像：
- 拥有3年国企财务会计背景，现全面转型商业数据分析方向
- 核心优势：能打通财务与业务壁垒，精准识别业务痛点，擅长商业分析与战略定位
- 定位非纯底层代码开发方向，而是业务驱动的数据分析与决策支持
- 技能栈：SQL（数据提取与分析）、Python（NLP/ML/数据处理）、Power BI（可视化看板搭建）、统计学模型
- 教育背景：英国南安普顿大学 商业分析与管理科学 硕士（2027届留学应届）
- 软实力：财务思维 + 数据分析双轮驱动，擅长业务报告与管理层汇报

请根据上述候选人画像与用户提供的 JD，严格返回如下 JSON 格式，不要包含任何额外文字：
{
  "matchScore": <0~100 的整数，表示整体匹配分>,
  "coreValueFit": "<简明描述候选人核心价值与该岗位的契合点，1~2句话>",
  "skillsMatch": ["<与JD匹配的技能/经验1>", "<匹配项2>", "<匹配项3>"],
  "uniqueEdge": "<候选人相对于普通数据分析候选人的独特竞争优势，1~2句话>"
}`;

// ── POST /api/match ───────────────────────────────────────────────────────────
app.post('/api/match', async (req, res) => {
  try {
    const { jd } = req.body;
    if (!jd?.trim()) {
      return res.status(400).json({ error: 'JD 内容不能为空' });
    }

    const apiKey = process.env.QWEN_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ error: 'QWEN_API_KEY 未配置，请检查 .env.local' });
    }

    const upstream = await fetch(
      'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: 'qwen-plus',
          messages: [
            { role: 'system', content: SYSTEM_PROMPT },
            { role: 'user', content: `请分析以下 JD 与候选人的匹配度：\n\n${jd}` },
          ],
          response_format: { type: 'json_object' },
          max_tokens: 1000,
        }),
      }
    );

    if (!upstream.ok) {
      const errText = await upstream.text();
      return res.status(upstream.status).json({ error: `上游 API 失败：${errText}` });
    }

    const data = await upstream.json();
    const content = data.choices?.[0]?.message?.content;
    if (!content) return res.status(500).json({ error: '模型未返回内容' });

    const parsed = JSON.parse(content);
    return res.json(parsed);
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`✅  服务已启动 → http://localhost:${PORT}`);
});
