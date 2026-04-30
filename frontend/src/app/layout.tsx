export const metadata = {
  title: 'Kraivor - Developer Intelligence Platform',
  description: 'One platform. Three products. Production-grade from day one.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
