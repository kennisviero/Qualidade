import { Pipe, PipeTransform } from '@angular/core';
import { TimeZoneEnum } from '../model/enum/timezone.enum';

@Pipe({
  name: 'timezone',
  standalone: true,
})
export class TimeZonePipe implements PipeTransform {
  constructor() {}

  transform(dateString: string | undefined): string {
    if (!dateString) {
      return '';
    }
    return this.formatDateTime(dateString);
  }

  /**
   * Method to format date time in MM/DD/YYYY HH:MM TZ
   * @param dateString
   * @returns
   */
  formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    // Format the date in MM/DD/YYYY
    const formattedDate = `${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}/${date.getFullYear()}`;
    // Format the time in HH:MM
    const formattedTime = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    return formattedDate + ' ' + formattedTime + ' ' + this.getTimeZone();
  }

  /**
   * Get user's current time zone.
   * @returns
   */
  getTimeZone(): string {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const date = new Date();
    const timeZoneOffset = -date.getTimezoneOffset() / 60; // offset in hours

    switch (timeZoneOffset) {
      case 5.5:
        return TimeZoneEnum.IST;
      case 5.0:
        return TimeZoneEnum.ET;
      case 6.0:
        return TimeZoneEnum.CT;
      case 7.0:
        return TimeZoneEnum.MT;
      case 8.0:
        return TimeZoneEnum.PT;
      default:
        return timeZone; // Fallback to the full time zone name if not a common U.S. time zone
    }
  }
}
