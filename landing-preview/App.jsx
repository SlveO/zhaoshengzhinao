import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0 },
};

const heroMetrics = [
  { value: "162 所", label: "已覆盖院校数据源" },
  { value: "182,000+", label: "已整理招生相关文档" },
  { value: "24/7", label: "在线招生咨询能力" },
];

function HeroPage() {
  return (
    <section className="relative min-h-[100svh] overflow-hidden bg-[#fbfdff] text-slate-950">
      <style>{`
        @keyframes silkFloatLeft { 0%,100%{transform:translate3d(-1.5%,0,0) scale(1) rotate(-1deg)} 50%{transform:translate3d(1.2%,-1.5%,0) scale(1.025) rotate(.5deg)} }
        @keyframes silkFloatRight { 0%,100%{transform:translate3d(1.2%,0,0) scale(1) rotate(1deg)} 50%{transform:translate3d(-1.5%,1.2%,0) scale(1.025) rotate(-.5deg)} }
        @keyframes glowBreath { 0%,100%{opacity:.48;transform:scale(1)} 50%{opacity:.76;transform:scale(1.06)} }
        @keyframes softSweep { 0%{transform:translateX(-16%) rotate(15deg);opacity:.08} 50%{opacity:.18} 100%{transform:translateX(16%) rotate(15deg);opacity:.08} }
        .hero-silk-left{animation:silkFloatLeft 16s ease-in-out infinite;transform-origin:12% 50%;filter:url(#heroSoftDisplace) drop-shadow(0 30px 90px rgba(14,165,233,.14))}
        .hero-silk-right{animation:silkFloatRight 17s ease-in-out infinite;transform-origin:88% 50%;filter:url(#heroSoftDisplace) drop-shadow(0 30px 90px rgba(14,165,233,.14))}
        .hero-ambient-glow{animation:glowBreath 11s ease-in-out infinite}
        .hero-light-sweep{animation:softSweep 13s ease-in-out infinite alternate}
      `}</style>

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_42%,rgba(255,255,255,1)_0%,rgba(255,255,255,.96)_31%,rgba(240,249,255,.70)_62%,rgba(251,253,255,1)_100%)]" />
      <div className="hero-ambient-glow absolute -left-24 top-16 h-[30rem] w-[30rem] rounded-full bg-sky-200/30 blur-3xl" />
      <div className="hero-ambient-glow absolute -right-24 top-12 h-[32rem] w-[32rem] rounded-full bg-cyan-200/26 blur-3xl" style={{ animationDelay: "-4s" }} />
      <div className="absolute left-1/2 top-[-10rem] h-[38rem] w-[58rem] -translate-x-1/2 rounded-full bg-white/72 blur-3xl" />

      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1600 900" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="heroLeftSilkA" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#e0f7ff" stopOpacity="0.07" />
            <stop offset="18%" stopColor="#7dd3fc" stopOpacity="0.31" />
            <stop offset="42%" stopColor="#38bdf8" stopOpacity="0.40" />
            <stop offset="64%" stopColor="#ffffff" stopOpacity="0.48" />
            <stop offset="82%" stopColor="#bae6fd" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.03" />
          </linearGradient>
          <linearGradient id="heroLeftSilkB" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.02" />
            <stop offset="28%" stopColor="#bae6fd" stopOpacity="0.34" />
            <stop offset="52%" stopColor="#0ea5e9" stopOpacity="0.28" />
            <stop offset="70%" stopColor="#ffffff" stopOpacity="0.50" />
            <stop offset="100%" stopColor="#67e8f9" stopOpacity="0.08" />
          </linearGradient>
          <linearGradient id="heroRightSilkA" x1="1" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e0f2fe" stopOpacity="0.06" />
            <stop offset="20%" stopColor="#7dd3fc" stopOpacity="0.30" />
            <stop offset="44%" stopColor="#22d3ee" stopOpacity="0.40" />
            <stop offset="66%" stopColor="#ffffff" stopOpacity="0.46" />
            <stop offset="84%" stopColor="#bae6fd" stopOpacity="0.27" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.02" />
          </linearGradient>
          <linearGradient id="heroRightSilkB" x1="1" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.02" />
            <stop offset="25%" stopColor="#cffafe" stopOpacity="0.34" />
            <stop offset="48%" stopColor="#0284c7" stopOpacity="0.26" />
            <stop offset="70%" stopColor="#ffffff" stopOpacity="0.50" />
            <stop offset="100%" stopColor="#93c5fd" stopOpacity="0.08" />
          </linearGradient>
          <filter id="heroSoftDisplace" x="-20%" y="-20%" width="140%" height="140%">
            <feTurbulence type="fractalNoise" baseFrequency="0.008 0.018" numOctaves="2" seed="11" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="10" xChannelSelector="R" yChannelSelector="G" />
          </filter>
          <filter id="heroGrain" x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
            <feComponentTransfer><feFuncA type="table" tableValues="0 0.03" /></feComponentTransfer>
          </filter>
        </defs>
        <g className="hero-silk-left">
          <path d="M-120 -40 C90 44 210 130 340 276 C455 405 432 506 310 660 C178 828 35 908 -122 954 Z" fill="url(#heroLeftSilkA)" />
          <path d="M-42 -80 C132 66 246 168 338 330 C421 476 373 600 230 774 C116 910 14 950 -92 982 Z" fill="url(#heroLeftSilkB)" opacity="0.68" />
          <path d="M-94 18 C70 110 190 220 292 366 C365 470 348 560 254 690 C148 834 46 908 -72 946" fill="none" stroke="rgba(255,255,255,.44)" strokeWidth="31" strokeLinecap="round" opacity="0.50" />
        </g>
        <g className="hero-silk-right">
          <path d="M1720 -40 C1512 48 1390 136 1265 284 C1150 420 1168 520 1296 674 C1428 834 1568 910 1724 956 Z" fill="url(#heroRightSilkA)" />
          <path d="M1642 -80 C1472 64 1352 176 1260 338 C1178 484 1228 608 1368 778 C1480 912 1586 952 1694 984 Z" fill="url(#heroRightSilkB)" opacity="0.68" />
          <path d="M1688 18 C1518 112 1390 224 1290 370 C1218 476 1240 566 1338 696 C1446 838 1548 910 1670 948" fill="none" stroke="rgba(255,255,255,.42)" strokeWidth="31" strokeLinecap="round" opacity="0.50" />
        </g>
        <rect width="1600" height="900" filter="url(#heroGrain)" opacity="0.38" />
      </svg>

      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[42rem] w-[54rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/80 blur-3xl" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[26rem] w-[38rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/88 blur-2xl" />
      <div className="hero-light-sweep pointer-events-none absolute left-0 right-0 top-[12%] h-52 bg-gradient-to-r from-transparent via-white/70 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent via-[#fbfdff]/85 to-[#f8fbff]" />

      <div className="relative z-10 flex min-h-[100svh] items-center justify-center px-6 py-12">
        <div className="mx-auto w-full max-w-6xl text-center">
          <motion.p initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }} className="mx-auto mb-6 w-fit text-center text-xs font-semibold tracking-[0.22em] text-sky-700 sm:text-sm">
            面向高校招生办的 AI 招生平台
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 26 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08, duration: 0.86, ease: [0.22, 1, 0.36, 1] }} className="mx-auto max-w-5xl">
            <p className="mb-3 text-4xl font-black tracking-[-0.06em] text-slate-950 sm:text-5xl lg:text-6xl">招生智脑</p>
            <h1 className="text-center text-4xl font-black leading-[1.06] tracking-[-0.065em] text-slate-950 sm:text-6xl lg:text-[4.58rem]">
              <span className="block whitespace-nowrap">懂心理的 <span className="bg-gradient-to-r from-sky-500 via-cyan-600 to-slate-900 bg-clip-text text-transparent">AI 招生官</span></span>
              <span className="block whitespace-nowrap">看得见的 <span className="bg-gradient-to-r from-slate-900 via-sky-700 to-cyan-500 bg-clip-text text-transparent">生源控制台</span></span>
            </h1>
          </motion.div>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18, duration: 0.72, ease: [0.22, 1, 0.36, 1] }} className="mx-auto mt-6 max-w-3xl text-center text-base font-light leading-7 text-slate-500 sm:text-lg">
            <span className="block">通过智能对话理解考生兴趣、专业偏好与升学焦虑，</span>
            <span className="block">并将分散的咨询内容沉淀为院校可复盘的生源数据。</span>
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.34, duration: 0.72, ease: [0.22, 1, 0.36, 1] }} className="mx-auto mt-9 max-w-3xl rounded-[1.45rem] border border-white/70 bg-white/54 px-4 py-3 shadow-[0_18px_56px_rgba(14,165,233,0.11)] backdrop-blur-md">
            <div className="grid gap-2 sm:grid-cols-3 sm:divide-x sm:divide-slate-200/80">
              {heroMetrics.map((item) => (
                <div key={item.value} className="px-3 py-2">
                  <div className="text-xl font-black tracking-[-0.04em] text-slate-950 sm:text-2xl">{item.value}</div>
                  <div className="mt-1 text-xs font-medium text-slate-500 sm:text-sm">{item.label}</div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

const leftMethods = [
  {
    title: "已识别身份",
    body: "广东 / 物理类 / 预估 585 分",
    desc: "具备明确报考场景，可进入后续线索判断。",
  },
  {
    title: "核心顾虑",
    body: "就业稳定性、转专业政策、与其他院校对比。",
    desc: "说明学生仍处于比较与犹豫阶段。",
  },
];

const rightMethods = [
  {
    title: "关注方向",
    body: "电子信息类专业",
    desc: "重点关注培养计划、就业去向与录取位次。",
  },
  {
    title: "画像沉淀",
    body: "初步学生画像已形成",
    desc: "可为后续意向评分与人工跟进提供依据。",
  },
];

function MethodCard({ title, body, desc, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.45 }}
      transition={{ duration: 0.42, delay, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-[18px] border border-slate-200/70 bg-white/68 px-4 py-3.5 shadow-[0_16px_42px_rgba(15,23,42,0.055)] backdrop-blur-xl"
    >
      <h3 className="text-[17px] font-black tracking-[-0.035em] text-slate-950">{title}</h3>
      <p className="mt-2 text-[13px] font-bold leading-5 text-sky-700">{body}</p>
      <p className="mt-1.5 text-[12.5px] leading-5 text-slate-500">{desc}</p>
    </motion.div>
  );
}

function ChatBubble({ role = "ai", delay = 0, children }) {
  const isStudent = role === "student";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.988 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, amount: 0.65 }}
      transition={{ duration: 0.32, delay, ease: [0.22, 1, 0.36, 1] }}
      className={`flex ${isStudent ? "justify-end" : "justify-start"}`}
    >
      <div className={`max-w-[92%] rounded-[15px] px-3 py-2 text-[10.8px] leading-[1.46] shadow-sm ${isStudent ? "rounded-br-md bg-[linear-gradient(135deg,#1cc8ea_0%,#16b5dd_100%)] text-white shadow-[0_10px_24px_rgba(14,165,233,0.16)]" : "rounded-bl-md border border-slate-200/80 bg-white text-slate-700 shadow-[0_7px_20px_rgba(15,23,42,0.05)]"}`}>
        {children}
      </div>
    </motion.div>
  );
}

function PhoneMockup() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14, scale: 0.985 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, amount: 0.35 }}
      transition={{ duration: 0.48, ease: [0.22, 1, 0.36, 1] }}
      className="relative z-[8] mx-auto w-[320px] origin-top"
    >
      <div className="absolute inset-0 rounded-[34px] bg-cyan-100/30 blur-2xl" />
      <div className="relative rounded-[34px] bg-[#071228] p-[7px] shadow-[0_26px_76px_rgba(2,132,199,0.16)]">
        <div className="overflow-hidden rounded-[27px] bg-[#f4f7fb]">
          <div className="flex h-8 items-center justify-between border-b border-slate-200/80 bg-white/92 px-5 text-[10px] text-slate-400">
            <span className="font-semibold">9:41</span>
            <span className="text-[12px] font-bold text-slate-700">招生智脑</span>
            <span className="font-semibold">5G</span>
          </div>
          <div className="space-y-1.5 px-3.5 py-2.5">
            <div className="mx-auto mb-1 w-fit rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-[10px] font-bold text-slate-600">院校官方招生咨询</div>
            <ChatBubble role="student" delay={0.42}>
              老师，我是广东物理类考生，预估 585 分，想了解贵校电子信息类专业，录取机会大吗？
            </ChatBubble>
            <ChatBubble role="ai" delay={0.72}>
              可以先参考近三年录取位次，再结合你的省份、科类和目标专业判断。电子信息类近年关注度较高，我也可以帮你对比就业方向和培养计划。
            </ChatBubble>
            <ChatBubble role="student" delay={1.02}>
              我比较关心以后就业，还有如果进校后想转专业，会不会很难？
            </ChatBubble>
            <ChatBubble role="ai" delay={1.32}>
              就业和转专业是很多考生都会重点关注的问题。你可以先看电子信息类的就业去向、企业类型和转专业政策。如果你愿意，我也可以根据你的分数和兴趣帮你判断是否适合填报。
            </ChatBubble>
            <ChatBubble role="student" delay={1.62}>
              我现在还在和另一所学校比较，主要担心专业发展和录取稳定性。
            </ChatBubble>
            <ChatBubble role="ai" delay={1.92}>
              明白。你目前更关注专业前景、录取把握和后续发展。我会结合你的分数、关注专业和顾虑点，给出更适合你的报考参考。
            </ChatBubble>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ConversationPage() {
  return (
    <section className="relative h-[100svh] min-h-[720px] overflow-hidden bg-[#f8fbff] text-slate-950">
      <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url('/page2-bg.png')" }} />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(248,251,255,0.88)_0%,rgba(248,251,255,0.72)_24%,rgba(248,251,255,0.62)_58%,rgba(248,251,255,0.84)_100%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_38%,rgba(255,255,255,0.88),rgba(255,255,255,0.25)_48%,transparent_74%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_16%_50%,rgba(186,230,253,0.23),transparent_26%),radial-gradient(circle_at_84%_50%,rgba(186,230,253,0.23),transparent_26%)]" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-[#f8fbff] via-[#f8fbff]/80 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-b from-transparent via-[#f8fbff]/85 to-[#f8fbff]" />

      <div className="relative z-10 flex h-full items-center justify-center px-6 py-4">
        <div className="relative mx-auto w-full max-w-[1260px] scale-[0.82] transform-gpu">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.48 }}
            className="mx-auto mb-5 max-w-5xl text-center"
          >
            <p className="mb-2 text-[15px] font-black tracking-[0.18em] text-sky-600">学生咨询端</p>
            <h2 className="whitespace-nowrap text-[56px] font-black leading-[1.04] tracking-[-0.06em] text-slate-950">学生在咨询，系统在理解</h2>
            <p className="mx-auto mt-4 max-w-4xl text-[17px] font-light leading-7 text-slate-500">
              招生智脑部署在高校官网、公众号、小程序与线下宣讲场景中，承接学生关于分数线、专业、就业、校园生活等问题的咨询，并在对话过程中自动提取省份、分数、关注方向与犹豫点。
            </p>
          </motion.div>

          <div className="relative mx-auto h-[500px] max-w-[1080px]">
            <div className="grid h-full grid-cols-[250px_1fr_250px] items-center gap-10">
              <div className="relative z-[8] flex h-full flex-col justify-center gap-[86px]">
                <MethodCard {...leftMethods[0]} delay={0.58} />
                <MethodCard {...leftMethods[1]} delay={1.02} />
              </div>
              <div className="relative z-[8] flex h-full items-start justify-center pt-[2px]">
                <PhoneMockup />
              </div>
              <div className="relative z-[8] flex h-full flex-col justify-center gap-[86px]">
                <MethodCard {...rightMethods[0]} delay={0.78} />
                <MethodCard {...rightMethods[1]} delay={1.22} />
              </div>
            </div>
          </div>

          <motion.p
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ delay: 2.12, duration: 0.42 }}
            className="relative z-[20] mx-auto mt-8 max-w-2xl text-center text-sm font-medium tracking-wide text-slate-500"
          >
            从回答问题开始，沉淀可分析的学生需求。
          </motion.p>
        </div>
      </div>
    </section>
  );
}

const leadModules = [
  {
    index: "01",
    title: "信息沉淀",
    desc: "记录学生省份、分数、关注专业、咨询问题与表达倾向。",
  },
  {
    index: "02",
    title: "意向识别",
    desc: "根据提问频次、关注深度与犹豫点，判断报考意愿和跟进优先级。",
  },
  {
    index: "03",
    title: "人工跟进",
    desc: "生成线索摘要、沟通重点与推荐材料，帮助招生老师优先联系。",
  },
];

const leadRows = [
  {
    name: "学生 A",
    profile: "广东 / 物理类 / 585 分",
    direction: "电子信息方向",
    focus: "就业去向、转专业、录取位次",
    status: "优先跟进",
    score: "92",
    active: true,
  },
  {
    name: "学生 B",
    profile: "湖南 / 物理类 / 601 分",
    direction: "计算机方向",
    focus: "保研机会、竞赛培养、培养方案",
    status: "建议联系",
    score: "84",
    active: false,
  },
  {
    name: "学生 C",
    profile: "广西 / 历史类 / 560 分",
    direction: "汉语言文学方向",
    focus: "分数线、就业方向、校园生活",
    status: "持续观察",
    score: "67",
    active: false,
  },
];

const currentLeadDetails = [
  { label: "学生画像", value: "广东 / 物理类 / 585 分 / 电子信息方向" },
  { label: "核心关注", value: "就业去向、转专业政策、近三年录取位次" },
  { label: "意向判断", value: "多次追问专业就业与录取可能性，报考意愿较高。" },
  { label: "建议动作", value: "建议招生老师 24 小时内人工跟进。" },
  { label: "推荐材料", value: "电子信息类就业案例、专业培养方案、近三年录取位次说明。" },
];

function LeadModuleItem({ index, title, desc, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.45 }}
      transition={{ delay, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="group min-w-0"
    >
      <div className="mb-3 flex items-baseline gap-2 border-b border-slate-200/70 pb-2">
        <span className="font-mono text-[12px] font-semibold text-slate-300">{index}</span>
        <h3 className="text-[17px] font-black tracking-[-0.035em] text-slate-950">{title}</h3>
      </div>
      <p className="text-[13px] font-light leading-6 text-slate-500">{desc}</p>
    </motion.div>
  );
}

function WorkbenchStep({ children, active }) {
  return (
    <span className={`inline-flex items-center border px-3 py-1.5 text-[12px] font-bold ${active ? "border-sky-300 bg-sky-50 text-sky-700" : "border-slate-200 bg-white/70 text-slate-500"}`}>
      {children}
    </span>
  );
}

function LeadRow({ lead, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.45 }}
      transition={{ delay: 0.34 + index * 0.07, duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
      className={`grid grid-cols-[72px_1fr_72px] items-center gap-4 border-b border-slate-100 px-5 py-3.5 last:border-b-0 ${lead.active ? "bg-sky-50/70 shadow-[inset_3px_0_0_rgba(14,165,233,0.65)]" : "bg-white/45"}`}
    >
      <div>
        <p className="text-[14px] font-black tracking-[-0.03em] text-slate-950">{lead.name}</p>
        <p className="mt-1 font-mono text-[11px] font-semibold text-slate-400">意向 {lead.score}</p>
      </div>
      <div className="min-w-0">
        <p className="text-[13px] font-bold text-slate-700">{lead.profile}</p>
        <p className="mt-1 text-[13px] text-slate-600">{lead.direction}</p>
        <p className="mt-1 truncate text-[12px] text-slate-400">关注：{lead.focus}</p>
      </div>
      <div className="text-right">
        <span className={`inline-flex whitespace-nowrap border px-2 py-1 text-[12px] font-black ${lead.active ? "border-sky-300 bg-white text-sky-700" : "border-slate-200 bg-white/75 text-slate-500"}`}>
          {lead.status}
        </span>
      </div>
    </motion.div>
  );
}

function CurrentLeadAdvice() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.35 }}
      transition={{ delay: 0.58, duration: 0.48, ease: [0.22, 1, 0.36, 1] }}
      className="grid gap-4 border-t border-slate-200/80 bg-[#f8fbff]/70 px-5 py-4 sm:grid-cols-[0.9fr_1.1fr]"
    >
      <div className="border-r border-slate-200/70 pr-4">
        <p className="text-[12px] font-bold text-slate-400">当前线索建议</p>
        <h4 className="mt-1 text-[18px] font-black tracking-[-0.04em] text-slate-950">24 小时内人工跟进</h4>
        <p className="mt-2 text-[12.5px] font-light leading-5 text-slate-500">该学生多次追问就业与录取可能性，已经进入高意向跟进区。</p>
      </div>
      <div className="grid gap-x-5 gap-y-2 sm:grid-cols-2">
        {currentLeadDetails.map((item) => (
          <div key={item.label} className={item.label === "推荐材料" ? "sm:col-span-2" : ""}>
            <p className="text-[11px] font-black text-sky-700/80">{item.label}</p>
            <p className="mt-0.5 text-[12.5px] font-medium leading-5 text-slate-600">{item.value}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function HighIntentWorkbench() {
  return (
    <motion.div
      initial={{ opacity: 0, x: 28, y: 18 }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.62, ease: [0.22, 1, 0.36, 1] }}
      className="relative mx-auto w-full max-w-[42rem]"
    >
      <div className="absolute -left-10 top-10 h-64 w-64 rounded-full bg-sky-200/24 blur-3xl" />
      <div className="absolute -right-8 bottom-8 h-72 w-72 rounded-full bg-cyan-200/20 blur-3xl" />
      <div className="relative overflow-hidden border border-white/85 bg-white/78 shadow-[0_28px_100px_rgba(14,165,233,0.13)] backdrop-blur-2xl [clip-path:polygon(0_0,94%_0,100%_8%,100%_100%,6%_100%,0_92%)]">
        <div className="flex items-start justify-between gap-5 border-b border-slate-200/80 px-6 py-5">
          <div>
            <p className="text-[12px] font-black tracking-[0.18em] text-sky-600">LEAD WORKBENCH</p>
            <h3 className="mt-1 text-[24px] font-black tracking-[-0.045em] text-slate-950">高意向生源工作台</h3>
            <p className="mt-2 max-w-[27rem] text-[13px] leading-6 text-slate-500">从咨询内容中提取画像、关注点与报考意向，把分散对话转成可执行的跟进清单。</p>
          </div>
          <div className="shrink-0 border border-sky-100 bg-sky-50/70 px-4 py-3 text-right">
            <p className="text-[11px] font-bold text-slate-400">今日新增</p>
            <p className="mt-1 text-[24px] font-black tracking-[-0.05em] text-sky-700">18</p>
            <p className="text-[11px] font-medium text-slate-400">条高意向线索</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200/80 px-6 py-4">
          <WorkbenchStep>咨询沉淀</WorkbenchStep>
          <span className="text-slate-300">→</span>
          <WorkbenchStep>标签提取</WorkbenchStep>
          <span className="text-slate-300">→</span>
          <WorkbenchStep>意向评分</WorkbenchStep>
          <span className="text-slate-300">→</span>
          <WorkbenchStep active>人工跟进</WorkbenchStep>
        </div>

        <div className="bg-white/45">
          <div className="grid grid-cols-[72px_1fr_72px] gap-4 border-b border-slate-100 px-5 py-2.5 text-[11px] font-black tracking-[0.12em] text-slate-400">
            <span>线索</span>
            <span>画像与关注点</span>
            <span className="text-right">动作</span>
          </div>
          {leadRows.map((lead, index) => (
            <LeadRow key={lead.name} lead={lead} index={index} />
          ))}
        </div>

        <CurrentLeadAdvice />
      </div>
    </motion.div>
  );
}

function LeadDashboardPage() {
  return (
    <section className="relative h-[100svh] overflow-hidden bg-[#f8fbff] text-slate-950">
      <style>{`
        @keyframes leadFloatLeft { 0%,100%{transform:translate3d(-1%,0,0) scale(1) rotate(-.6deg)} 50%{transform:translate3d(.8%,-1.2%,0) scale(1.018) rotate(.3deg)} }
        @keyframes leadFloatRight { 0%,100%{transform:translate3d(1%,0,0) scale(1) rotate(.6deg)} 50%{transform:translate3d(-.8%,1%,0) scale(1.018) rotate(-.3deg)} }
        .lead-silk-left{animation:leadFloatLeft 18s ease-in-out infinite;transform-origin:12% 50%;filter:drop-shadow(0 30px 80px rgba(14,165,233,.12))}
        .lead-silk-right{animation:leadFloatRight 19s ease-in-out infinite;transform-origin:88% 50%;filter:drop-shadow(0 30px 80px rgba(14,165,233,.12))}
      `}</style>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_42%,rgba(255,255,255,1)_0%,rgba(255,255,255,.96)_31%,rgba(240,249,255,.72)_62%,rgba(251,253,255,1)_100%)]" />
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1600 900" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="leadSilkL" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#e0f7ff" stopOpacity="0.04" />
            <stop offset="25%" stopColor="#7dd3fc" stopOpacity="0.22" />
            <stop offset="50%" stopColor="#38bdf8" stopOpacity="0.28" />
            <stop offset="72%" stopColor="#ffffff" stopOpacity="0.40" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.02" />
          </linearGradient>
          <linearGradient id="leadSilkR" x1="1" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e0f2fe" stopOpacity="0.04" />
            <stop offset="25%" stopColor="#7dd3fc" stopOpacity="0.22" />
            <stop offset="50%" stopColor="#22d3ee" stopOpacity="0.27" />
            <stop offset="72%" stopColor="#ffffff" stopOpacity="0.40" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <g className="lead-silk-left">
          <path d="M-130 -40 C78 48 208 142 336 292 C444 420 420 520 306 668 C178 832 36 914 -128 956 Z" fill="url(#leadSilkL)" />
          <path d="M-86 30 C84 120 186 226 288 372 C360 478 344 568 250 698 C146 838 42 910 -78 950" fill="none" stroke="rgba(255,255,255,.42)" strokeWidth="30" strokeLinecap="round" opacity="0.45" />
        </g>
        <g className="lead-silk-right">
          <path d="M1730 -40 C1514 50 1390 142 1262 294 C1156 426 1178 528 1300 676 C1430 834 1570 914 1728 956 Z" fill="url(#leadSilkR)" />
          <path d="M1688 30 C1514 122 1394 230 1292 374 C1222 480 1244 570 1340 700 C1448 840 1550 912 1672 952" fill="none" stroke="rgba(255,255,255,.42)" strokeWidth="30" strokeLinecap="round" opacity="0.45" />
        </g>
      </svg>
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[42rem] w-[56rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/82 blur-3xl" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-36 bg-gradient-to-b from-transparent via-[#fbfdff]/85 to-[#f8fbff]" />

      <div className="relative z-10 flex h-full items-center justify-center px-6 py-6">
        <div className="mx-auto grid w-full max-w-[86rem] scale-[0.91] transform-gpu items-center gap-12 lg:grid-cols-[0.92fr_1.08fr] xl:gap-16">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.45 }}
            transition={{ duration: 0.58, ease: [0.22, 1, 0.36, 1] }}
            className="min-w-0"
          >
            <div className="mb-8">
              <p className="text-[24px] font-black tracking-[-0.05em] text-slate-950">招生智脑</p>
              <p className="mt-2 text-[13px] font-semibold tracking-[0.14em] text-sky-700">高校数字招生解决方案</p>
            </div>
            <p className="mb-3 text-[15px] font-black tracking-[0.16em] text-sky-600">生源线索识别</p>
            <h2 className="max-w-[43rem] text-[48px] font-black leading-[1.06] tracking-[-0.064em] text-slate-950 lg:text-[58px]">
              <span className="block whitespace-nowrap">从咨询数据中，</span>
              <span className="block whitespace-nowrap">识别值得跟进的学生</span>
            </h2>
            <p className="mt-6 max-w-[41rem] text-[16px] font-light leading-8 text-slate-500">
              招生智脑将学生在咨询过程中的省份、分数、关注专业、犹豫点与报考意向自动结构化，形成线索评分与跟进建议，帮助招生老师优先联系更有转化可能的学生。
            </p>
            <div className="mt-9 grid max-w-[43rem] gap-6 sm:grid-cols-3">
              {leadModules.map((item, index) => (
                <LeadModuleItem key={item.title} {...item} delay={0.18 + index * 0.08} />
              ))}
            </div>
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ delay: 0.52, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="mt-8 text-[17px] font-black tracking-[-0.035em] text-slate-800"
            >
              让招生老师把时间花在最值得联系的学生身上。
            </motion.p>
          </motion.div>

          <HighIntentWorkbench />
        </div>
      </div>
    </section>
  );
}

const streamLanes = [
  ["就业去向", "转专业政策", "录取位次", "宣传内容缺口", "宣讲重点", "招生动作"],
  ["电子信息类", "专业培养方案", "就业案例", "家长顾虑", "渠道触达", "内容优化"],
  ["公众号菜单", "推文选题", "宣讲会问答", "政策说明", "高频问题", "招生参谋"],
  ["学生关注变化", "专业热度", "信息入口", "表达优化", "材料更新", "数据驱动"],
  ["真实咨询反馈", "宣传策略", "内容补充", "院校表达", "下一轮招生", "策略复盘"],
];

function DataStreamLane({ words, index, side = "left" }) {
  const repeated = [...words, ...words, ...words, ...words, ...words];
  const duration = 30 + index * 4;
  const delay = -index * 4;
  return <div className="data-stream-lane" style={{ top: `${13 + index * 17}%` }}><div className="data-stream-track" style={{ animationDuration: `${duration}s`, animationDelay: `${delay}s` }}>{repeated.map((word, wordIndex) => <span key={`${side}-${index}-${word}-${wordIndex}`} className="data-stream-word" style={{ fontSize: `${index % 2 === 0 ? 21 : 16}px`, opacity: index % 2 === 0 ? 0.18 : 0.13 }}>{word}</span>)}</div></div>;
}
function DataStreamPanel({ side = "left" }) { return <div className={`data-stream-panel data-stream-panel-${side}`}>{streamLanes.map((words, index) => <DataStreamLane key={`${side}-${index}`} words={side === "right" ? [...words].reverse() : words} index={index} side={side} />)}</div>; }
function DataStreamWords() {
  return (
    <div className="pointer-events-none absolute inset-0 hidden overflow-hidden lg:block" aria-hidden="true">
      <style>{`
        @keyframes dataStreamMove { from { transform: translate3d(-42%, 0, 0); } to { transform: translate3d(0%, 0, 0); } }
        .data-stream-panel { position:absolute; top:0; bottom:0; overflow:hidden; pointer-events:none; z-index:3; }
        .data-stream-panel-left { left:0; width:30vw; -webkit-mask-image:linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.80) 12%, rgba(0,0,0,0.82) 48%, rgba(0,0,0,0.36) 70%, rgba(0,0,0,0.10) 86%, rgba(0,0,0,0) 100%); mask-image:linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.80) 12%, rgba(0,0,0,0.82) 48%, rgba(0,0,0,0.36) 70%, rgba(0,0,0,0.10) 86%, rgba(0,0,0,0) 100%); }
        .data-stream-panel-right { right:0; width:30vw; -webkit-mask-image:linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.10) 14%, rgba(0,0,0,0.36) 30%, rgba(0,0,0,0.82) 52%, rgba(0,0,0,0.80) 88%, rgba(0,0,0,0) 100%); mask-image:linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.10) 14%, rgba(0,0,0,0.36) 30%, rgba(0,0,0,0.82) 52%, rgba(0,0,0,0.80) 88%, rgba(0,0,0,0) 100%); }
        .data-stream-lane { position:absolute; left:-26%; right:-26%; height:42px; transform:translateY(-50%); white-space:nowrap; }
        .data-stream-track { display:flex; width:max-content; align-items:center; gap:50px; animation-name:dataStreamMove; animation-timing-function:linear; animation-iteration-count:infinite; will-change:transform; }
        .data-stream-word { display:inline-block; color:#020617; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; font-weight:900; letter-spacing:-0.045em; line-height:1; text-shadow:0 16px 34px rgba(15,23,42,0.12), 0 2px 6px rgba(15,23,42,0.05); filter:blur(0.04px); }
      `}</style>
      <div className="absolute -left-72 top-[8%] z-[1] h-[78%] w-[36rem] rounded-full bg-[radial-gradient(circle_at_center,rgba(56,189,248,.16),transparent_65%)] blur-[42px]" />
      <div className="absolute -right-72 top-[8%] z-[1] h-[78%] w-[36rem] rounded-full bg-[radial-gradient(circle_at_center,rgba(34,211,238,.14),transparent_65%)] blur-[42px]" />
      <div className="absolute inset-0 z-[2] bg-[radial-gradient(ellipse_at_50%_50%,rgba(255,255,255,0.96)_0%,rgba(255,255,255,0.90)_30%,rgba(255,255,255,0.52)_56%,rgba(255,255,255,0)_78%),linear-gradient(180deg,rgba(248,251,255,0.76),rgba(248,251,255,0)_28%,rgba(248,251,255,0)_74%,rgba(248,251,255,0.78))]" />
      <DataStreamPanel side="left" />
      <DataStreamPanel side="right" />
    </div>
  );
}

const topics = [
  { id: "overview", label: "本周总览", dashboardLabel: "本周总览" },
  { id: "content", label: "内容优化", dashboardLabel: "宣传内容优化" },
  { id: "speech", label: "宣讲重点", dashboardLabel: "宣讲重点调整" },
  { id: "channel", label: "渠道建议", dashboardLabel: "渠道触达建议" },
];

const dashboardData = {
  overview: {
    inputTitle: "从数据洞察，到招生动作",
    inputDesc: "系统把咨询中反复出现的问题，转化为宣传材料、宣讲内容与渠道触达的优化建议。",
    left: {
      title: "学生关注变化",
      desc: "学生和家长最近真正关心什么。",
      items: [
        { title: "就业去向咨询上升", desc: "电子信息类、计算机方向的就业去向持续被追问。" },
        { title: "转专业政策被反复追问", desc: "学生希望知道入校后的调整空间和具体规则。" },
        { title: "电子信息类专业热度提升", desc: "咨询集中在培养计划、就业企业和录取稳定性。" },
        { title: "家长更关注录取稳定性", desc: "家长倾向要求位次参考和近三年录取解释。" },
      ],
    },
    middle: {
      title: "宣传内容缺口",
      desc: "反复咨询说明学校材料哪里没有讲清楚。",
      items: [
        { title: "电子信息类就业案例不足", desc: "现有材料对就业去向、企业类型和岗位说明不够具体。" },
        { title: "转专业政策解释不够直观", desc: "规则入口分散，学生难以快速理解申请条件与流程。" },
        { title: "近三年录取位次入口不明显", desc: "考生需要在多个页面间查找，影响填报判断效率。" },
        { title: "专业培养方案表达偏学术化", desc: "课程介绍缺少面向考生的通俗解释和发展路径。" },
      ],
    },
    right: {
      title: "建议招生动作",
      desc: "招生办下一步可以直接执行的优化建议。",
      items: [
        { title: "发布《电子信息类专业就业去向解析》推文", desc: "用真实去向、企业类型和岗位方向回应就业顾虑。" },
        { title: "在公众号菜单新增“转专业政策说明”", desc: "把申请条件、时间节点和问题集中呈现。" },
        { title: "宣讲会增加“近三年录取位次解读”", desc: "帮助学生和家长建立更稳定的报考预期。" },
        { title: "面向广东物理类考生推送专业就业案例", desc: "用高频咨询主题反向指导渠道内容触达。" },
      ],
    },
  },
  content: {
    inputTitle: "把反复被问的问题，变成下一轮内容补充",
    inputDesc: "当学生持续追问同一类信息，说明宣传材料需要更清楚、更靠前、更适合考生理解。",
    left: {
      title: "学生关注变化",
      desc: "内容优化视角下的高频咨询信号。",
      items: [
        { title: "就业去向说明需求集中", desc: "学生希望看到毕业行业、企业类型与岗位方向。" },
        { title: "录取位次查询频率高", desc: "填报前更需要稳定、易理解的历史参考信息。" },
        { title: "专业差异解释不足", desc: "学生难区分电子信息、自动化与计算机方向的培养差别。" },
        { title: "校园生活问题被持续提出", desc: "住宿、社团与学习支持也影响学生对学校的判断。" },
      ],
    },
    middle: {
      title: "宣传内容缺口",
      desc: "现有宣传材料需要补足的表达位置。",
      items: [
        { title: "就业案例缺少具体人物和路径", desc: "建议从“去向列表”升级为“学生发展案例”。" },
        { title: "专业介绍缺少考生语言", desc: "减少纯培养方案表述，增加“适合什么学生”。" },
        { title: "录取数据入口不够集中", desc: "把近三年位次、分数与专业热度放到同一入口。" },
        { title: "常见问题缺少场景化回答", desc: "将高频咨询转成 FAQ，而不是分散在多篇文章中。" },
      ],
    },
    right: {
      title: "建议招生动作",
      desc: "面向内容团队的下一步更新建议。",
      items: [
        { title: "新增“专业就业案例库”专题页", desc: "按专业整理毕业去向、就业行业和典型发展路径。" },
        { title: "重写电子信息类专业介绍首屏", desc: "先讲培养方向、就业场景，再进入课程和平台资源。" },
        { title: "制作近三年录取位次说明图", desc: "用一张图解释分数、位次和填报参考方式。" },
        { title: "把高频问题沉淀为公众号菜单入口", desc: "让学生在咨询前就能找到关键说明。" },
      ],
    },
  },
  speech: {
    inputTitle: "把咨询里的犹豫点，变成宣讲会要主动讲清楚的重点",
    inputDesc: "宣讲不是重复介绍学校，而是优先回答学生和家长最担心、最影响决策的问题。",
    left: {
      title: "学生关注变化",
      desc: "适合放进宣讲会的关键关注点。",
      items: [
        { title: "就业稳定性被家长高频提到", desc: "家长更关心毕业后是否稳定、发展是否清晰。" },
        { title: "专业发展空间影响选择", desc: "学生希望知道专业未来方向和行业认可度。" },
        { title: "转专业规则影响报考信心", desc: "不确定性会降低学生填报意愿。" },
        { title: "录取把握需要被解释", desc: "位次、分数和专业热度需要用通俗方式说明。" },
      ],
    },
    middle: {
      title: "宣传内容缺口",
      desc: "宣讲中容易被忽略但学生最需要的信息。",
      items: [
        { title: "专业优势讲得多，选择风险讲得少", desc: "学生还需要知道自己是否适合该专业。" },
        { title: "就业成果缺少可感知案例", desc: "只讲就业率不够，需要讲行业、岗位和成长路径。" },
        { title: "政策说明缺少问答化表达", desc: "转专业、保研、培养计划应转成常见问题形式。" },
        { title: "家长视角内容不足", desc: "录取稳定性、城市发展和生活成本也需要回应。" },
      ],
    },
    right: {
      title: "建议招生动作",
      desc: "面向宣讲老师的内容调整建议。",
      items: [
        { title: "宣讲会增加“专业就业去向”板块", desc: "用案例讲清楚电子信息类未来能做什么。" },
        { title: "增加“录取位次如何参考”说明", desc: "帮助考生把自己的分数放进合理判断区间。" },
        { title: "设置“转专业政策三问三答”", desc: "主动解释申请条件、难度和时间节点。" },
        { title: "准备家长版答疑页", desc: "集中回应稳定性、培养质量和就业发展。" },
      ],
    },
  },
  channel: {
    inputTitle: "把不同渠道的咨询反馈，变成更精准的触达建议",
    inputDesc: "系统根据咨询来源与问题类型，帮助招生办判断哪些内容应该放在哪个渠道、推给哪类人。",
    left: {
      title: "学生关注变化",
      desc: "渠道触达视角下的咨询信号。",
      items: [
        { title: "公众号入口更集中承接政策问题", desc: "分数线、位次、转专业政策最适合做菜单入口。" },
        { title: "宣讲现场更适合解释专业差异", desc: "面对面场景能更好回应专业选择和发展顾虑。" },
        { title: "小程序适合承接个性化查询", desc: "省份、科类、分数和专业方向可以形成快速检索。" },
        { title: "家长更偏好稳定、清楚的材料", desc: "需要更明确的就业、升学和录取说明。" },
      ],
    },
    middle: {
      title: "宣传内容缺口",
      desc: "不同渠道当前承接不充分的内容。",
      items: [
        { title: "公众号菜单缺少政策聚合入口", desc: "学生需要快速找到录取位次和转专业说明。" },
        { title: "短内容缺少专业对比表达", desc: "不同专业之间的差异没有被清楚拆开。" },
        { title: "线下宣讲资料更新不及时", desc: "线上高频问题没有快速反馈到宣讲材料中。" },
        { title: "家长群材料偏零散", desc: "缺少一份可转发、可保存的家长关切说明。" },
      ],
    },
    right: {
      title: "建议招生动作",
      desc: "面向渠道运营的下一步触达建议。",
      items: [
        { title: "公众号新增“录取位次 / 转专业政策”入口", desc: "优先承接被反复追问的政策型咨询。" },
        { title: "小程序增加按省份和科类的专业推荐页", desc: "让学生从自身条件进入专业理解。" },
        { title: "线下宣讲同步更新高频问题清单", desc: "把线上咨询反馈带回宣讲现场。" },
        { title: "向家长群推送就业案例与录取说明合集", desc: "用稳定、清楚的材料降低家庭决策顾虑。" },
      ],
    },
  },
};

function TopicTabs({ activeTopic, onChange }) {
  return <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.45 }} transition={{ delay: 0.16, duration: 0.58, ease: [0.22, 1, 0.36, 1] }} className="mx-auto mb-4 max-w-5xl rounded-[1.45rem] border border-white/70 bg-white/52 px-5 py-3 shadow-[0_18px_64px_rgba(14,165,233,0.09)] backdrop-blur-xl"><div className="mb-3 flex flex-col justify-between gap-2 text-center sm:flex-row sm:items-end sm:text-left"><div><h3 className="text-lg font-black tracking-[-0.03em] text-slate-950">策略视角</h3></div><p className="max-w-xl text-sm leading-6 text-slate-500">切换不同视角，查看系统如何把咨询反馈转化为招生办的下一步动作。</p></div><div className="flex flex-wrap justify-center gap-2.5 sm:justify-start">{topics.map((topic) => { const active = activeTopic === topic.id; return <button key={topic.id} type="button" onClick={() => onChange(topic.id)} className={`rounded-full border px-4 py-1.5 text-sm font-bold shadow-sm transition-all duration-300 ${active ? "border-sky-300 bg-sky-500 text-white shadow-[0_12px_32px_rgba(14,165,233,0.18)]" : "border-white/70 bg-white/62 text-slate-500 hover:border-sky-200 hover:bg-white/90 hover:text-sky-700"}`}>{topic.label}</button>; })}</div></motion.div>;
}
function DashboardHeader({ activeTopic }) { return <div className="mb-3 flex flex-col justify-between gap-2 px-1 sm:flex-row sm:items-end"><div><h3 className="text-xl font-black tracking-[-0.04em] text-slate-950 sm:text-2xl">招生策略报告</h3></div><p className="max-w-2xl text-sm font-medium leading-6 text-slate-500 sm:text-right">当前视角：<span className="font-black text-sky-700">{activeTopic.dashboardLabel}</span><br className="hidden sm:block" />分析链路：学生问了什么 → 学校哪里没讲清楚 → 下一步该怎么做</p></div>; }
function TopicSummary({ data }) { return <motion.div key={`summary-${data.inputTitle}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.28 }} className="mb-3 rounded-2xl border border-sky-100 bg-sky-50/55 px-4 py-2 text-sm leading-6 text-slate-600"><span className="font-black text-slate-950">{data.inputTitle}</span><span className="mx-2 text-slate-300">/</span>{data.inputDesc}</motion.div>; }
function StrategyList({ items, hintLabel }) {
  const primaryItems = items.slice(0, 2);
  const previewItems = items.slice(2, 4);
  return (
    <div className="mt-3">
      <div className="space-y-2.5">
        {primaryItems.map((item, index) => (
          <motion.div key={item.title} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 + index * 0.04, duration: 0.28, ease: [0.22, 1, 0.36, 1] }} className="rounded-2xl border border-slate-100 bg-white/74 px-3.5 py-2.5 shadow-sm">
            <div className="flex items-start gap-2.5">
              <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-50 text-[11px] font-black text-sky-700 ring-1 ring-sky-100">{index + 1}</span>
              <div>
                <h5 className="text-[14px] font-black tracking-[-0.02em] text-slate-800">{item.title}</h5>
                <p className="mt-0.5 text-[12.5px] leading-5 text-slate-500">{item.desc}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
      <div className="relative mt-2.5 overflow-hidden rounded-2xl border border-slate-100/80 bg-white/42 px-3.5 py-2.5">
        <div className="space-y-2">
          {previewItems.map((item, index) => (
            <motion.div key={item.title} initial={{ opacity: 0, y: 6 }} animate={{ opacity: index === 0 ? 0.58 : 0.34, y: 0 }} transition={{ delay: 0.15 + index * 0.05, duration: 0.28, ease: [0.22, 1, 0.36, 1] }} className="flex items-center gap-2.5">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-50 text-[11px] font-black text-slate-400 ring-1 ring-slate-100">{index + 3}</span>
              <h5 className="truncate text-[13px] font-black tracking-[-0.02em] text-slate-600">{item.title}</h5>
            </motion.div>
          ))}
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-11 bg-gradient-to-b from-white/0 via-white/68 to-white/96" />
      </div>
      <div className="mt-2 text-center text-[12px] font-semibold tracking-wide text-slate-400">还有 {previewItems.length} 条{hintLabel}</div>
    </div>
  );
}
function DashboardCard({ title, desc, children, delay = 0 }) { return <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.4, ease: [0.22, 1, 0.36, 1] }} className="rounded-[1.45rem] border border-white/72 bg-white/66 p-4 shadow-[0_18px_64px_rgba(14,165,233,0.09)]"><h4 className="text-lg font-black tracking-[-0.03em] text-slate-950">{title}</h4><p className="mt-1 text-[13px] leading-5 text-slate-500">{desc}</p>{children}</motion.div>; }
function Dashboard({ topicId }) {
  const data = dashboardData[topicId];
  const activeTopic = topics.find((topic) => topic.id === topicId) || topics[0];
  return <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.28 }} transition={{ delay: 0.24, duration: 0.62, ease: [0.22, 1, 0.36, 1] }} className="mx-auto max-w-[84rem] rounded-[1.8rem] border border-white/70 bg-white/50 p-3.5 shadow-[0_24px_84px_rgba(14,165,233,0.12)] backdrop-blur-2xl"><DashboardHeader activeTopic={activeTopic} /><AnimatePresence mode="wait"><motion.div key={topicId} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}><TopicSummary data={data} /><div className="grid gap-3.5 lg:grid-cols-3"><DashboardCard title={data.left.title} desc={data.left.desc} delay={0.02}><StrategyList items={data.left.items} hintLabel={data.left.title} /></DashboardCard><DashboardCard title={data.middle.title} desc={data.middle.desc} delay={0.08}><StrategyList items={data.middle.items} hintLabel={data.middle.title} /></DashboardCard><DashboardCard title={data.right.title} desc={data.right.desc} delay={0.14}><StrategyList items={data.right.items} hintLabel={data.right.title} /></DashboardCard></div></motion.div></AnimatePresence></motion.div>;
}
function DashboardPage() {
  const [activeTopic, setActiveTopic] = useState("overview");
  return <section className="relative h-[100svh] overflow-hidden bg-[#f8fbff] text-slate-950"><div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_7%,rgba(186,230,253,0.38),transparent_34%),radial-gradient(circle_at_10%_42%,rgba(56,189,248,0.11),transparent_28%),radial-gradient(circle_at_90%_42%,rgba(34,211,238,0.10),transparent_30%),linear-gradient(180deg,#f8fbff_0%,#ffffff_12%,#eef8ff_100%)]" /><div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-[#f8fbff] via-[#f8fbff]/80 to-transparent" /><div className="pointer-events-none absolute left-1/2 top-[23%] h-[28rem] w-[56rem] -translate-x-1/2 rounded-full bg-white/70 blur-3xl" /><DataStreamWords /><div className="relative z-10 flex h-full items-center justify-center px-6 py-6"><div className="mx-auto w-full max-w-[88rem] scale-[0.80] transform-gpu"><motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.45 }} transition={{ duration: 0.58, ease: [0.22, 1, 0.36, 1] }} className="mx-auto mb-4 max-w-4xl text-center"><p className="mb-2 text-sm font-black tracking-[0.20em] text-sky-500">招生策略反哺</p><h2 className="text-center text-5xl font-black leading-tight tracking-[-0.05em] text-slate-950">让真实咨询数据，<br />指导下一次招生动作</h2><p className="mx-auto mt-4 max-w-3xl text-center text-[17px] font-light leading-7 text-slate-500"><span className="block">招生智脑汇总学生与家长在咨询中的高频问题、关注专业与犹豫原因，</span><span className="block">生成宣传内容优化、宣讲重点调整和渠道触达建议，帮助高校从经验招生走向数据驱动招生。</span></p></motion.div><TopicTabs activeTopic={activeTopic} onChange={setActiveTopic} /><Dashboard topicId={activeTopic} /><motion.p initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.35 }} transition={{ delay: 0.58, duration: 0.5, ease: [0.22, 1, 0.36, 1] }} className="mx-auto mt-4 max-w-2xl text-center text-sm font-medium tracking-wide text-slate-500">每一次咨询反馈，都会成为下一轮招生优化的依据。</motion.p></div></div></section>;
}



const deploymentFeatures = [
  {
    title: "接入现有渠道",
    desc: "官网、公众号、小程序、宣讲二维码等入口统一承接咨询。",
  },
  {
    title: "院校专属配置",
    desc: "支持学校名称、Logo、主题色、知识库与招生数据定制。",
  },
  {
    title: "统一沉淀数据",
    desc: "来自不同入口的咨询统一汇入后台，形成可持续分析的招生数据资产。",
  },
];

const deployScenes = [
  {
    image: "/deploy-main.png",
    title: "多渠道统一接入",
    desc: "官网、公众号、小程序与线下宣讲入口，统一接入同一套招生智脑。",
    nav: "总览",
  },
  {
    image: "/deploy-website.png",
    title: "官网咨询入口",
    desc: "在高校招生官网中嵌入 AI 咨询入口，不改变原有官网结构。",
    nav: "官网",
  },
  {
    image: "/deploy-miniprogram.png",
    title: "公众号 / 小程序承接",
    desc: "学生无需下载新 App，在学校已有微信生态中完成招生咨询。",
    nav: "微信生态",
  },
  {
    image: "/deploy-offline.png",
    title: "宣讲扫码接入",
    desc: "线下宣讲、招生海报与二维码，都可以成为持续咨询入口。",
    nav: "线下宣讲",
  },
  {
    image: "/deploy-config.png",
    title: "院校配置中心",
    desc: "学校名称、Logo、知识库、话术风格与权限体系均可专属配置。",
    nav: "配置中心",
  },
];

function DeploymentFeature({ title, desc, delay = 0 }) {
  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.45 }}
      transition={{ delay, duration: 0.46, ease: [0.22, 1, 0.36, 1] }}
      className="border-l border-sky-200/80 pl-4"
    >
      <h3 className="text-[17px] font-black tracking-[-0.03em] text-slate-950">{title}</h3>
      <p className="mt-1.5 text-[14px] leading-6 text-slate-500">{desc}</p>
    </motion.div>
  );
}

function DeploymentSceneNav({ activeIndex, onChange }) {
  return (
    <div className="mt-3 grid grid-cols-5 gap-2 rounded-[1.25rem] border border-white/70 bg-white/52 p-2 shadow-[0_14px_44px_rgba(14,165,233,0.08)] backdrop-blur-xl">
      {deployScenes.map((scene, index) => {
        const active = activeIndex === index;
        return (
          <button
            key={scene.nav}
            type="button"
            onClick={() => onChange(index)}
            className={`rounded-[0.95rem] px-2.5 py-2 text-[12px] font-black tracking-[-0.02em] transition-all duration-300 ${
              active
                ? "bg-sky-500 text-white shadow-[0_10px_26px_rgba(14,165,233,0.18)]"
                : "bg-white/55 text-slate-500 hover:bg-white hover:text-sky-700"
            }`}
          >
            {scene.nav}
          </button>
        );
      })}
    </div>
  );
}

function DeploymentPage() {
  const [activeScene, setActiveScene] = useState(0);
  const currentScene = deployScenes[activeScene];

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveScene((index) => (index + 1) % deployScenes.length);
    }, 4200);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section className="relative h-[100svh] overflow-hidden bg-[#f8fbff] text-slate-950">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(186,230,253,0.34),transparent_34%),radial-gradient(circle_at_82%_18%,rgba(34,211,238,0.18),transparent_31%),linear-gradient(180deg,#f8fbff_0%,#ffffff_18%,#eef8ff_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-[16%] h-[24rem] w-[58rem] -translate-x-1/2 rounded-full bg-white/70 blur-3xl" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-[#f8fbff] via-[#f8fbff]/86 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-28 bg-gradient-to-b from-transparent via-[#f8fbff]/88 to-[#f8fbff]" />

      <div className="relative z-10 flex h-full items-center justify-center px-6 py-6">
        <div className="mx-auto grid w-full max-w-[86rem] scale-[0.90] transform-gpu items-center gap-8 lg:grid-cols-[0.92fr_1.08fr]">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.45 }}
            transition={{ duration: 0.58, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-[560px]"
          >
            <p className="mb-3 text-[14px] font-black tracking-[0.20em] text-sky-500">多渠道部署</p>
            <h2 className="text-[42px] font-black leading-[1.08] tracking-[-0.055em] text-slate-950 sm:text-[52px] lg:text-[58px]">
              一套招生智脑，<br />接入高校现有每个招生入口
            </h2>
            <p className="mt-5 max-w-[540px] text-[16px] font-light leading-7 text-slate-500">
              招生智脑可部署于高校官网、公众号、小程序与线下宣讲场景中，并结合院校专属品牌、招生知识库与管理权限配置，为每所高校搭建自己的 AI 招生官。
            </p>

            <div className="mt-7 grid gap-4">
              {deploymentFeatures.map((item, index) => (
                <DeploymentFeature key={item.title} {...item} delay={0.1 + index * 0.06} />
              ))}
            </div>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.45 }}
              transition={{ delay: 0.36, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="mt-7 text-[14px] font-semibold tracking-wide text-slate-500"
            >
              不改变高校原有招生触点，只让每个触点更智能。
            </motion.p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.985 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ delay: 0.12, duration: 0.62, ease: [0.22, 1, 0.36, 1] }}
            className="relative"
          >
            <div className="absolute -inset-5 rounded-[2.3rem] bg-sky-200/18 blur-3xl" />
            <div className="relative overflow-hidden rounded-[2rem] border border-white/80 bg-white/58 p-3.5 shadow-[0_28px_90px_rgba(14,165,233,0.16)] backdrop-blur-2xl">
              <div className="relative overflow-hidden rounded-[1.45rem] border border-slate-100/80 bg-slate-50/70">
                <AnimatePresence mode="wait">
                  <motion.img
                    key={currentScene.image}
                    src={currentScene.image}
                    alt={currentScene.title}
                    initial={{ opacity: 0, x: 18, scale: 0.992 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    exit={{ opacity: 0, x: -18, scale: 0.992 }}
                    transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
                    className="h-[390px] w-full object-contain object-center"
                  />
                </AnimatePresence>
              </div>

              <div className="flex items-end justify-between gap-5 px-2 pt-3">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentScene.title}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
                    className="min-h-[54px]"
                  >
                    <h3 className="text-[20px] font-black tracking-[-0.04em] text-slate-950">{currentScene.title}</h3>
                    <p className="mt-1 text-[14px] font-medium leading-6 text-slate-500">{currentScene.desc}</p>
                  </motion.div>
                </AnimatePresence>
                <div className="hidden shrink-0 items-center gap-1.5 pb-1 sm:flex">
                  {deployScenes.map((scene, index) => (
                    <button
                      key={scene.nav}
                      type="button"
                      onClick={() => setActiveScene(index)}
                      aria-label={`切换到${scene.nav}`}
                      className={`h-1.5 rounded-full transition-all duration-300 ${activeScene === index ? "w-8 bg-sky-500" : "w-2 bg-slate-200 hover:bg-sky-200"}`}
                    />
                  ))}
                </div>
              </div>
            </div>

            <DeploymentSceneNav activeIndex={activeScene} onChange={setActiveScene} />
          </motion.div>
        </div>
      </div>
    </section>
  );
}



const conversionValues = [
  {
    title: "从触达到留存",
    desc: "不同入口进入的学生，不再是一次性咨询，而是进入统一线索池。",
  },
  {
    title: "从识别到行动",
    desc: "系统不只判断谁值得跟进，还给出沟通重点和推荐材料。",
  },
  {
    title: "从转化到复盘",
    desc: "跟进结果反哺渠道、内容和宣讲策略，持续优化下一轮招生。",
  },
];

function ConversionValueItem({ title, desc, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.45 }}
      transition={{ delay: 0.16 + index * 0.06, duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
      className="border-l border-sky-200/80 pl-4"
    >
      <h3 className="text-[18px] font-black tracking-[-0.04em] text-slate-950">{title}</h3>
      <p className="mt-1.5 text-[14px] leading-6 text-slate-500">{desc}</p>
    </motion.div>
  );
}

function ConversionLoopPage() {
  return (
    <section className="relative h-[100svh] overflow-hidden bg-[#f8fbff] text-slate-950">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_24%_35%,rgba(186,230,253,0.45),transparent_34%),radial-gradient(circle_at_78%_28%,rgba(56,189,248,0.16),transparent_30%),linear-gradient(180deg,#f8fbff_0%,#ffffff_42%,#eef8ff_100%)]" />
      <div className="pointer-events-none absolute left-[12%] top-[12%] h-[26rem] w-[36rem] rounded-full bg-sky-200/18 blur-3xl" />
      <div className="pointer-events-none absolute right-[-8rem] bottom-[-10rem] h-[34rem] w-[34rem] rounded-full bg-cyan-200/18 blur-3xl" />
      <div className="relative z-10 flex h-full items-center justify-center px-6 py-8">
        <div className="mx-auto grid w-full max-w-[86rem] scale-[0.92] transform-gpu items-center gap-10 lg:grid-cols-[1.12fr_0.88fr]">
          <motion.div
            initial={{ opacity: 0, x: -24, scale: 0.985 }}
            whileInView={{ opacity: 1, x: 0, scale: 1 }}
            viewport={{ once: true, amount: 0.32 }}
            transition={{ duration: 0.66, ease: [0.22, 1, 0.36, 1] }}
            className="relative"
          >
            <div className="absolute -inset-6 rounded-[2.5rem] bg-sky-200/20 blur-3xl" />
            <div className="relative overflow-hidden rounded-[2rem] border border-white/80 bg-white/60 p-3.5 shadow-[0_30px_90px_rgba(14,165,233,0.15)] backdrop-blur-2xl">
              <img
                src="/convert-dashboard.png"
                alt="高校招生运营工作台 / 生源转化闭环"
                className="h-[600px] w-full rounded-[1.45rem] object-contain object-center"
              />
            </div>
          </motion.div>

          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.45 }}
            transition={{ duration: 0.58, ease: [0.22, 1, 0.36, 1] }}
            className="relative"
          >
            <div className="mb-4 flex items-center gap-3">
              <span className="h-px w-10 bg-sky-300/80" />
              <p className="text-[14px] font-black tracking-[0.18em] text-sky-600">生源转化闭环</p>
            </div>
            <h2 className="max-w-[34rem] text-[48px] font-black leading-[1.08] tracking-[-0.06em] text-slate-950 lg:text-[56px]">
              把“来咨询的学生”，变成“值得持续经营的生源”
            </h2>
            <p className="mt-5 max-w-[36rem] text-[17px] font-light leading-8 text-slate-500">
              招生智脑将官网、公众号、小程序与线下宣讲中的学生咨询统一沉淀，结合画像识别、意向分级和触达建议，帮助招生办持续跟进高潜学生，提高优质生源转化效率。
            </p>

            <div className="mt-8 space-y-5">
              {conversionValues.map((item, index) => (
                <ConversionValueItem key={item.title} {...item} index={index} />
              ))}
            </div>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.45 }}
              transition={{ delay: 0.42, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="mt-8 max-w-[34rem] text-[15px] font-semibold leading-7 tracking-wide text-slate-500"
            >
              招生智脑不只是回答问题，而是帮助高校把每一次咨询变成可运营的招生机会。
            </motion.p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function BusinessModelPage() {
  return (
    <section className="relative h-[100svh] overflow-hidden bg-[#f8fbff] text-slate-950">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_12%,rgba(186,230,253,0.46),transparent_35%),radial-gradient(circle_at_16%_66%,rgba(56,189,248,0.13),transparent_30%),radial-gradient(circle_at_86%_58%,rgba(34,211,238,0.12),transparent_32%),linear-gradient(180deg,#f8fbff_0%,#ffffff_42%,#eef8ff_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-[38%] h-[28rem] w-[60rem] -translate-x-1/2 rounded-full bg-white/65 blur-3xl" />
      <div className="relative z-10 flex h-full items-center justify-center px-6 py-8">
        <div className="mx-auto flex w-full max-w-[88rem] scale-[0.90] transform-gpu flex-col">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.45 }}
            transition={{ duration: 0.58, ease: [0.22, 1, 0.36, 1] }}
            className="mx-auto max-w-5xl text-center"
          >
            <p className="mb-3 text-[14px] font-black tracking-[0.20em] text-sky-600">商业模式</p>
            <h2 className="text-balance text-[48px] font-black leading-[1.08] tracking-[-0.06em] text-slate-950 lg:text-[58px]">
              用一次招生宣传预算，换来全年在线的智能招生能力
            </h2>
            <p className="mx-auto mt-5 max-w-4xl text-[17px] font-light leading-8 text-slate-500">
              招生智脑采用面向高校的 SaaS 年费模式，为不同类型院校提供从标准咨询承接到定制化招生数据分析的多层级服务，让高校用更可度量的方式投入招生宣传预算。
            </p>
          </motion.div>

          <div className="mt-8 grid items-stretch gap-5 lg:grid-cols-[1.08fr_0.92fr]">
            <motion.div
              initial={{ opacity: 0, y: 22 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.32 }}
              transition={{ delay: 0.12, duration: 0.58, ease: [0.22, 1, 0.36, 1] }}
              className="relative overflow-hidden rounded-[2rem] border border-white/80 bg-white/60 p-3.5 shadow-[0_28px_80px_rgba(14,165,233,0.13)] backdrop-blur-2xl"
            >
              <img src="/value-compare.png" alt="采购价值对照" className="h-[430px] w-full rounded-[1.45rem] object-contain object-center" />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 22 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.32 }}
              transition={{ delay: 0.2, duration: 0.58, ease: [0.22, 1, 0.36, 1] }}
              className="relative overflow-hidden rounded-[2rem] border border-white/80 bg-white/60 p-3.5 shadow-[0_28px_80px_rgba(14,165,233,0.12)] backdrop-blur-2xl"
            >
              <img src="/service-version.png" alt="服务版本阶梯" className="h-[430px] w-full rounded-[1.45rem] object-contain object-center" />
            </motion.div>
          </div>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ delay: 0.36, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="mx-auto mt-7 max-w-4xl text-center text-[18px] font-semibold leading-7 tracking-wide text-slate-500"
          >
            招生智脑不是增加一项宣传支出，而是把原有招生预算转化为可持续运营的数字能力。
          </motion.p>
        </div>
      </div>
    </section>
  );
}

function RoadmapFinalPage() {
  return (
    <section className="relative h-[100svh] overflow-hidden bg-[#f8fbff] text-slate-950">
      <img src="/roadmap-bg.png" alt="发展路线图背景" className="pointer-events-none absolute inset-0 h-full w-full object-cover object-center opacity-[0.18]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_24%,rgba(255,255,255,0.86),rgba(255,255,255,0.54)_42%,rgba(248,251,255,0.84)_75%),linear-gradient(180deg,#f8fbff_0%,rgba(248,251,255,0.82)_42%,#eef8ff_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-[48%] h-[36rem] w-[68rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/72 blur-3xl" />
      <div className="relative z-10 flex h-full items-center justify-center px-6 py-7">
        <div className="mx-auto flex w-full max-w-[88rem] scale-[0.90] transform-gpu flex-col items-center">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.45 }}
            transition={{ duration: 0.58, ease: [0.22, 1, 0.36, 1] }}
            className="mx-auto max-w-5xl text-center"
          >
            <p className="mb-3 text-[14px] font-black tracking-[0.20em] text-sky-600">发展路线图</p>
            <h2 className="text-balance text-[50px] font-black leading-[1.08] tracking-[-0.06em] text-slate-950 lg:text-[62px]">
              从试点院校，到区域招生数据网络
            </h2>
            <p className="mx-auto mt-5 max-w-4xl text-[17px] font-light leading-8 text-slate-500">
              招生智脑将从少量试点院校开始，验证咨询承接、线索转化与策略反哺效果，再通过标杆案例扩展至更多高校，逐步形成面向区域招生的数据智能网络。
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.985 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true, amount: 0.32 }}
            transition={{ delay: 0.14, duration: 0.62, ease: [0.22, 1, 0.36, 1] }}
            className="mt-8 w-full max-w-[74rem] overflow-hidden rounded-[2rem] border border-white/80 bg-white/66 p-3.5 shadow-[0_30px_90px_rgba(14,165,233,0.15)] backdrop-blur-2xl"
          >
            <img src="/roadmap-main.png" alt="招生智脑发展路线图" className="h-[410px] w-full rounded-[1.45rem] object-contain object-center" />
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ delay: 0.32, duration: 0.52, ease: [0.22, 1, 0.36, 1] }}
            className="mt-7 text-center text-[26px] font-black leading-tight tracking-[-0.04em] text-slate-950 lg:text-[32px]"
          >
            从被动答疑，到主动招生；从经验判断，到数据驱动。
          </motion.p>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  return <main className="overflow-x-hidden bg-[#fbfdff]"><HeroPage /><ConversationPage /><LeadDashboardPage /><DashboardPage /><DeploymentPage /><ConversionLoopPage /><BusinessModelPage /><RoadmapFinalPage /></main>;
}
