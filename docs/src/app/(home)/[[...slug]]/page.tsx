import { getApiVersions, source } from '@/lib/source';
import { getMDXComponents } from '@/mdx-components';
import { buttonVariants } from 'fumadocs-ui/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from 'fumadocs-ui/components/ui/popover';
import { createRelativeLink } from 'fumadocs-ui/mdx';
import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
} from 'fumadocs-ui/page';
import { cn } from 'fumadocs-ui/utils/cn';
import { ChevronDown } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';

export default async function Page(props: {
  params: Promise<{ slug?: string[] }>;
}) {
  const params = await props.params;
  const slug = params.slug || [];
  const page = source.getPage(slug);
  if (!page) notFound();

  // Detect if this is an API reference page: /docs/api/[section] or /docs/api/[section]/[version]
  let apiSection: string | null = null;
  let apiVersionSlug: string[] = [];
  if (slug[0] === 'api' && slug.length >= 2) {
    apiSection = slug[1];
    if (slug.length > 2) {
      apiVersionSlug = slug.slice(2);
    }
  }

  let versionItems: { label: string; slug: string[] }[] = [];
  if (apiSection) {
    versionItems = await getApiVersions(apiSection);
  }

  const MDXContent = page.data.body;

  return (
    <DocsPage toc={page.data.toc} full={page.data.full}>
      <div className="flex flex-row w-full">
        <DocsTitle>{page.data.title}</DocsTitle>
        <div className="ml-auto">
          {apiSection && versionItems.length > 1 && (
            <Popover>
              <PopoverTrigger
                className={cn(
                  buttonVariants({
                    color: 'secondary',
                    size: 'sm',
                    className: 'gap-2',
                  })
                )}>
                {(() => {
                  // Find the current version label
                  let currentLabel = 'Current';
                  if (apiVersionSlug.length > 0) {
                    const found = versionItems.find(
                      (item) =>
                        item.label !== 'Current' &&
                        apiVersionSlug[0] === item.label
                    );
                    if (found) currentLabel = found.label;
                  }
                  return (
                    <>
                      API Version: {currentLabel}
                      <ChevronDown className="size-3.5 text-fd-muted-foreground" />
                    </>
                  );
                })()}
              </PopoverTrigger>
              <PopoverContent className="flex flex-col overflow-auto">
                {versionItems.map((item) => {
                  // Build the href for each version
                  const href =
                    item.label === 'Current'
                      ? `/api/${apiSection}`
                      : `/api/${apiSection}/${item.label}`;
                  // Highlight current version
                  const isCurrent =
                    (item.label === 'Current' && apiVersionSlug.length === 0) ||
                    (item.label !== 'Current' &&
                      apiVersionSlug[0] === item.label);
                  return (
                    <Link
                      key={item.label}
                      href={href}
                      className={cn(
                        'px-3 py-1 rounded hover:bg-fd-muted',
                        isCurrent && 'font-bold bg-fd-muted'
                      )}>
                      API version: {item.label}
                    </Link>
                  );
                })}
              </PopoverContent>
            </Popover>
          )}
        </div>
      </div>
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <MDXContent
          components={getMDXComponents({
            // this allows you to link to other pages with relative file paths
            a: createRelativeLink(source, page),
          })}
        />
      </DocsBody>
    </DocsPage>
  );
}

export async function generateStaticParams() {
  return source.generateParams();
}

export async function generateMetadata(props: {
  params: Promise<{ slug?: string[] }>;
}) {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  let title = `c/ua Docs: ${page.data.title}`;
  if (page.url.includes('api')) title = `c/ua API: ${page.data.title}`;

  return {
    title,
    description: page.data.description,
  };
}
