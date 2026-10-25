import { Component, Input, ViewChild, ElementRef } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-textarea-field',
  templateUrl: './textarea-field.component.html',
  styleUrls: ['./textarea-field.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: TextareaFieldComponent,
      multi: true,
    },
  ],
  standalone: true,
  imports: [NgIf],
})
export class TextareaFieldComponent implements ControlValueAccessor {
  @Input() elementPlaceHolder!: string;
  @Input() elementId!: string;
  @Input() elementName!: string;
  @Input() required?: boolean = false;
  @Input() rows: number = 18;
  @Input() showLabel: boolean = true;
  @ViewChild('textarea') textarea!: ElementRef<HTMLTextAreaElement>;

  value: string = '';
  onTouchedFn: any;
  onValueChangeFn: any;
  isDisabled: boolean = false;

  onChange(target: any) {
    this.onValueChangeFn(target.value);
    this.onTouchedFn();
  }

  writeValue(obj: any): void {
    this.value = obj;
  }

  registerOnChange(fn: any): void {
    this.onValueChangeFn = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouchedFn = fn;
  }

  setDisabledState?(isDisabled: boolean): void {
    this.isDisabled = isDisabled;
  }
}
