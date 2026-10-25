import { Pipe, PipeTransform } from '@angular/core';
import { UtilityService } from '../services/utility.service';

@Pipe({
  name: 'expandRequirementName',
  standalone: true,
})
export class ExpandRequirementNamePipe implements PipeTransform {
  constructor(private utilityService: UtilityService) {}

  transform(name: string): string {
    return this.utilityService.expandRequirementName(name);
  }
}
