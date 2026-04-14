import Sidebar from './Sidebar'
import Header from './Header'

export default function MainLayout({ children, currentPage, onNavigate }) {
  return (
    <div className="flex w-screen h-screen bg-background">
      <Sidebar currentPage={currentPage} onNavigate={onNavigate} />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto ml-64 p-8 lg:p-12 pt-24 lg:pt-24">
          {children}
        </main>
      </div>
    </div>
  )
}
