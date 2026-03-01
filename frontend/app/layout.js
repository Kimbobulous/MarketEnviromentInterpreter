export const metadata = {
  title: "Market Environment Interpreter",
  description: "MVP dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
