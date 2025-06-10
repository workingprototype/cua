import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

import Image from 'next/image';
import logoBlack from '@/assets/logo-black.svg';
import logoWhite from '@/assets/logo-white.svg';
import { HomeIcon } from 'lucide-react';

/**
 * Shared layout configurations
 *
 * you can customise layouts individually from:
 * Home Layout: app/(home)/layout.tsx
 * Docs Layout: app/docs/layout.tsx
 */
export const baseOptions: BaseLayoutProps = {
  nav: {
    title: (
      <>
        <Image
          width={30}
          height={30}
          src={logoBlack}
          aria-label="Logo"
          className="block dark:hidden"
          alt="Logo"
        />
        <Image
          width={30}
          height={30}
          src={logoWhite}
          aria-label="Logo"
          className="hidden dark:block"
          alt="Logo"
        />
        Cua Documentation
      </>
    ),
  },
  githubUrl: 'https://github.com/trycua/cua',
  links: [
    {
      url: '/home',
      text: 'Documentation Home',
      icon: <HomeIcon />,
    },
    {
      url: 'https://trycua.com',
      text: 'cua home',
      type: 'icon',
      icon: <HomeIcon />,
    },
  ],
};
