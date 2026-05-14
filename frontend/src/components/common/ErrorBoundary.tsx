import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
          <div className="text-center max-w-md">
            <div className="text-4xl mb-4">!</div>
            <h2 className="text-xl font-semibold text-text mb-2">页面出现异常</h2>
            <p className="text-muted text-sm mb-6">请刷新页面重试，或返回首页</p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-2 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition"
              >
                刷新页面
              </button>
              <button
                onClick={() => { window.location.href = '/' }}
                className="px-6 py-2 border border-border text-text rounded-lg font-semibold hover:bg-gray-50 transition"
              >
                返回首页
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
