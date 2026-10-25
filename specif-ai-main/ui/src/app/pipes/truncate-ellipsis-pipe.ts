import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'truncateWithEllipsis',
  standalone: true,
})
export class TruncateEllipsisPipe implements PipeTransform {
  constructor() {}

  transform(text: string | undefined, maxLength: number = 180): string | null {
    if (!text) {
      return null;
    }
    if (text.length > maxLength) {
      return text.substring(0, maxLength) + '...';
    }
    return text;
  }
}
