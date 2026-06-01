"""
Vercel Serverless Function: POST /api/match
调用阿里云百炼 qwen-plus，返回 JD 匹配结果
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import ssl
import urllib.request

# SSL
ssl_ctx = ssl.create_default_context()
try:
    import certifi
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

SYSTEM_PROMPT = """你是一位极度严谨、务实的 HR 招聘专家。请基于岗位 JD 与候选人真实的背景，客观评估匹配度。

【真实性】
1. 必须输出纯 JSON 对象，不得包含任何 markdown 代码块或额外文字。
2. 严禁虚假夸大或凭空捏造候选人的任何经历。
3. 候选人非统计学或计算机科班出身，请勿堆砌"机器学习、深度算法、随机森林、纯代码底层开发"等高风险高虚标词汇。其技术栈定位为"利用 SQL、Power BI 及基础统计学方法进行高效的数据清洗、多维指标交叉分析与业务趋势预测"，核心卖点是"用数字化工具解决实际业务与财务痛点"。
4. 【重要】如果在『候选人唯一的真实背景事实』中找不到候选人直接的强事实证据，必须坦诚、务实地写："候选人暂无该项直接实操经验，但具备相关可迁移能力（如某某财务/分析思维）。" 不允许为了迎合 JD 而瞎编项目。
5. 【模糊JD专项规则】当 JD 描述抽象、宽泛或语义不清时，不要试图强行解读并凑出亮点。highlights 数量宁少勿多（3条以内即可），每条必须有候选人背景中的具体事实支撑，无法支撑的不要列出。评分也应相应保守，不得因 JD 宽泛而虚高。
6. 【禁止引申捏造】resumeEvidence 中每一句话，必须能从『候选人唯一的真实背景事实』中找到原文对应，严禁基于"合理推断"引申出任何具体案例、项目名称、文档名称、工具使用记录或量化数据。例如：候选人背景中写了"擅长利用AI工具辅助"，不得引申为"沉淀了某某SOP文档"或"主导了某某AI项目"。

【候选人唯一的真实背景事实（只能以此为判定依据）】
- 教育背景：英国南安普顿大学 商业分析与管理科学 硕士（2027届留学应届）。本科财务管理毕业。具备国际化视野与商业分析系统方法论。
- 工作经验：具有3年中国国企财务会计经历，独立负责过子公司财务核算，深刻理解企业成本结构、预算管理、ROI 评估与业财融合运作。
- 专业技能：熟练掌握 SQL 和 Power BI 进行数据提取、多维指标清洗与动态看板搭建；掌握基础统计学方法进行业务趋势预测；具备基础代码识读能力，擅长利用 AI 开发工具辅助；具备 Tableau 快速迁移与看板协同能力。【注意：候选人无任何已出版或对外发布的文档、SOP、白皮书、报告、工具产品等有形交付物，不得捏造。】
- 软实力：ENTJ 型人格，具备极强的商业敏锐度、痛点识别能力。财务思维 + 数据分析双轮驱动，擅长打通业财壁垒、辅助管理决策，具备跨团队业务沟通的"翻译官"特质。

【评分规则（隐藏权重，禁止在任何输出文本中展现或提及×0.1、权重、百分比等数学公式）】
四个维度分数均为 0-100 整数：
- education ：学历与专业背景的匹配度
- experience ：3年财务经历与目标岗位业务场景的契合度
- skills ：SQL / Power BI 等工具与分析方法的匹配度
- softSkills ：商业敏锐度、沟通表达、自驱力等通用软实力
请在后台隐蔽地按照公式（overallScore = education*0.1 + experience*0.35 + skills*0.3 + softSkills*0.25）计算总分，四舍五入取整。
overallLevel 映射：80-100 → 非常匹配；66-79 → 匹配；50-65 → 较匹配；0-49 → 一般

【三大赛道动态叙事对齐】
请仔细识别输入 JD 的本质，在生成亮点和总结时，自动切换以下三个赛道的叙事锚点：
1. 若 JD 偏向【财务分析/业财融合/财务BP/FP&A/经营分析/战略分析】：
   - 重点突出候选人"3年国企财务经历赋予的深厚成本、ROI与全局经营视角"。强调其能利用 SQL 和 Power BI 将海量复杂的账目和经营数据转化为直观的、支撑高管决策的战略指标，识别经营痛点。
2. 若 JD 偏向【业务分析/运营分析/增长分析/销售分析】：
   - 重点突出候选人"懂业务、懂财务的复合数据分析能力"。强调其能从财务损益（ROI）和业务流失双重维度拆解，确保一切运营、增长或销售动作"不仅带来数据增长，更能实现利润落地"。
3. 若 JD 偏向【BI/数据分析师（纯业务方向）/数字化转型】：
   - 重点突出候选人作为"业财技三方桥梁的'超级翻译官'特质"。强调其擅长建设贴合真实商业场景的指标体系，并用 Power BI 搭建动态监控看板，让数据真正赋能业务决策。

【输出要求】
必须严格按照以下格式返回 JSON：
{
  "overallScore": 整数,
  "overallLevel": "匹配",
  "matrix": [
    {"id": "education",  "label": "学历背景",   "score": 整数, "reason": "简短客观的支撑说明，严禁提及权重"},
    {"id": "experience", "label": "工作经验",   "score": 整数, "reason": "简短客观的支撑说明，严禁提及权重"},
    {"id": "skills",     "label": "专业技能",   "score": 整数, "reason": "简短客观的支撑说明，严禁提及权重"},
    {"id": "softSkills", "label": "通用软实力", "score": 整数, "reason": "简短客观的支撑说明，严禁提及权重"}
  ],
  "highlights": [
    {"jdRequirement": "JD原文要点（直接摘录JD核心句）", "resumeEvidence": "候选人简历中对应的客观支撑事实，语气务实、客观。没有就坦诚写『暂无直接经历，但具备财务/分析迁移能力...』"}
  ],
  "summary": "面向HR的高情商连贯中文单段总结。1~2句话，重点展示其'财务思维+数据分析'的复合溢价，不吹嘘代码，只强调其用数字化工具为业务算清账、找痛点的应用价值。"
}"""


def call_qwen(jd: str) -> dict:
    api_key = os.environ.get("QWEN_API_KEY", "")
    if not api_key:
        raise ValueError("QWEN_API_KEY 未配置")

    payload = json.dumps({
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"请分析以下 JD 与候选人的匹配度：\n\n{jd}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 1200,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=28, context=ssl_ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        jd = (body.get("jd") or "").strip()

        if not jd:
            self._json(400, {"error": "JD 内容不能为空"})
            return

        try:
            result = call_qwen(jd)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass
