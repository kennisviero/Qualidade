import { Component, ChangeDetectorRef, AfterViewInit } from '@angular/core';
import { LoadingService } from '../../../services/loading.service';
import { NgxLoadingModule } from 'ngx-loading';

@Component({
  selector: 'app-loading',
  templateUrl: './loading.component.html',
  styleUrls: ['./loading.component.scss'],
  standalone: true,
  imports: [NgxLoadingModule],
})
export class LoadingComponent implements AfterViewInit {
  loading$ = this.loadingService.loading$;
  isLoading = false;

  constructor(
    private loadingService: LoadingService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngAfterViewInit() {
    this.loading$.subscribe((change) => {
      this.isLoading = change;
      this.cdr.detectChanges();
    });
  }
}
