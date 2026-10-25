import { FileTypeEnum } from '../model/enum/file-type.enum';
import { Navigation } from '@angular/router';

export function getDescriptionFromInput(
  input: string | undefined,
): string | null {
  const enumKey = Object.keys(FileTypeEnum).find(
    (key) => key === input?.toUpperCase().replace(/\s+/g, ''),
  );
  return enumKey ? FileTypeEnum[enumKey as keyof typeof FileTypeEnum] : null;
}

export function truncateWithEllipsis(
  text: string | undefined,
  maxLength: number = 180,
): string | null {
  if (!text) {
    return null;
  }
  if (text.length > maxLength) {
    return text.substring(0, maxLength) + '...';
  }
  return text;
}

export function getNavigationParams(navigation: Navigation | null) {
  return {
    projectId: navigation?.extras?.state?.['id'],
    folderName: navigation?.extras?.state?.['folderName'],
    fileName: navigation?.extras?.state?.['fileName'],
    selectedRequirement: navigation?.extras?.state?.['req'],
    data: navigation?.extras?.state?.['data'],
  };
}
