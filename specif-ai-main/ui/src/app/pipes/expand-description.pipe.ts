import { Pipe, PipeTransform } from '@angular/core';
import { FileTypeEnum } from '../model/enum/file-type.enum';

@Pipe({
  name: 'expandDescription',
  standalone: true,
})
export class ExpandDescriptionPipe implements PipeTransform {
  constructor() {}

  transform(input: string | undefined): string | null {
    const enumKey = Object.keys(FileTypeEnum).find(
      (key) => key === input?.toUpperCase().replace(/\s+/g, ''),
    );
    return enumKey ? FileTypeEnum[enumKey as keyof typeof FileTypeEnum] : null;
  }
}
