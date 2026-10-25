import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LoggerModule, NgxLoggerLevel } from 'ngx-logger';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { NgxSmartModalModule } from 'ngx-smart-modal';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { NgIconsModule } from '@ng-icons/core';
import { APP_ICONS } from '../../constants/icons.constants';

@NgModule({
  imports: [
    CommonModule,
    LoggerModule.forRoot({
      level: NgxLoggerLevel.DEBUG,
      serverLogLevel: NgxLoggerLevel.ERROR,
    }),
    MatProgressBarModule,
    NgxSmartModalModule,
    FormsModule,
    ReactiveFormsModule,
    BrowserAnimationsModule,

    NgIconsModule.withIcons({ ...APP_ICONS }),
  ],
  exports: [NgIconsModule],
})
export class SharedModule {}
