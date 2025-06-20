import { DocsLayout } from "fumadocs-ui/layouts/docs";
import type { ReactNode } from "react";
import { baseOptions } from "@/app/layout.config";
import { source } from "@/lib/source";
import { Home, Library, Cloud, Globe } from "lucide-react";

export default function Layout({ children }: { children: ReactNode }) {
	return (
		<DocsLayout
			tree={source.pageTree}
			sidebar={{
				tabs: [
					{
						url: "/home",
						title: "Home",
						description: "Welcome to the C/ua Documentation",
						icon: <Home />,
					},
					{
						url: "/api",
						title: "API Reference",
						description: "API Reference for C/ua libraries and services",
						icon: <Globe />,
					},
				],
			}}
			{...baseOptions}
		>
			{children}
		</DocsLayout>
	);
}
