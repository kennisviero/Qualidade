import { Injectable } from '@angular/core';
import { Observable, combineLatest } from 'rxjs';
import { map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root',
})
export class SearchService {
  /**
   * Generic search function that can be used with any type of data
   * @param items$ Observable of items to search through
   * @param searchTerm$ Observable of search term
   * @param searchFields Array of field names to search in
   * @returns Observable of filtered items
   */
  filterItems<T>(
    items$: Observable<T[]>,
    searchTerm$: Observable<string>,
    searchFields: (item: T) => (string | undefined)[],
  ): Observable<T[]> {
    return combineLatest([items$, searchTerm$]).pipe(
      map(([items, term]) => {
        if (!term) return items;
        return items.filter((item) => {
          const fields = searchFields(item);
          return fields.some((field) =>
            field?.toLowerCase().includes(term.toLowerCase()),
          );
        });
      }),
    );
  }
}
