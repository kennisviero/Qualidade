import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  Output,
  Renderer2,
  OnDestroy,
} from '@angular/core';

@Component({
  selector: 'hai-dropdown',
  templateUrl: './dropdown.component.html',
  styleUrls: ['./dropdown.component.scss'],
})
export class DropdownComponent implements OnDestroy {
  @Input() selectedOption: string = '';
  @Input() options: string[] = [];
  @Output() selectionChange = new EventEmitter<string>();

  isOpen = false;
  private globalClickListener: (() => void) | null = null;

  constructor(
    private elementRef: ElementRef,
    private renderer: Renderer2,
  ) {}

  toggleDropdown() {
    this.isOpen = !this.isOpen;

    if (this.isOpen) {
      this.globalClickListener = this.renderer.listen(
        'document',
        'click',
        (event: Event) => {
          this.handleClickOutside(event);
        },
      );
    } else {
      this.removeGlobalClickListener();
    }
  }

  selectOption(option: string) {
    this.selectedOption = option;
    this.selectionChange.emit(option);
    this.closeDropdown();
  }

  handleClickOutside(event: Event) {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.closeDropdown();
    }
  }

  closeDropdown() {
    this.isOpen = false;
    this.removeGlobalClickListener();
  }

  removeGlobalClickListener() {
    if (this.globalClickListener) {
      this.globalClickListener();
      this.globalClickListener = null;
    }
  }

  ngOnDestroy() {
    this.removeGlobalClickListener();
  }
}
