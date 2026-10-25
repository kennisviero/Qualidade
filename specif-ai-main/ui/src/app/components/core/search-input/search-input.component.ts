import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { distinctUntilChanged } from 'rxjs/operators';
import { heroMagnifyingGlass } from '@ng-icons/heroicons/outline';
import { NgIconComponent, provideIcons } from '@ng-icons/core';

@Component({
  selector: 'app-search-input',
  templateUrl: './search-input.component.html',
  styleUrls: ['./search-input.component.scss'],
  standalone: true,
  imports: [ReactiveFormsModule, NgIconComponent],
  viewProviders: [provideIcons({ heroMagnifyingGlass })]
})
export class SearchInputComponent {
  @Input() placeholder: string = 'Search...';
  @Output() searchChange = new EventEmitter<string>();

  searchControl = new FormControl('');

  constructor() {
    this.searchControl.valueChanges
      .pipe(distinctUntilChanged())
      .subscribe((value) => {
        this.searchChange.emit(value?.toLowerCase() || '');
      });
  }

  clearSearch() {
    this.searchControl.setValue('');
  }
}
