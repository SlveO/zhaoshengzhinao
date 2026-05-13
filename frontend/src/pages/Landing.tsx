import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-blue-50 to-white">
      <div className="text-center max-w-lg px-6">
        <h1 className="text-4xl font-bold text-text mb-4">高考志愿填报助手</h1>
        <p className="text-lg text-muted mb-8">通过智能对话了解你的兴趣和价值观，为你推荐最匹配的大学专业</p>
        <div className="flex gap-4 justify-center">
          <Link to="/register" className="px-8 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition">开始使用</Link>
          <Link to="/login" className="px-8 py-3 border border-border text-text rounded-lg font-semibold hover:bg-gray-50 transition">登录</Link>
        </div>
      </div>
    </div>
  )
}
