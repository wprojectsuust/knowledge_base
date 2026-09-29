/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  devIndicators: false,
  // префикс пути, если сайт живёт не в корне домена (деплой: karrad.tech/uunit)
  basePath: process.env.BASE_PATH || "",
};

export default nextConfig;
